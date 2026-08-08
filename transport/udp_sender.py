"""Reliable UDP sender — sliding-window Go-Back-N with timeout/retransmit.

Protocol overview
-----------------
1. Sender reads file in MAX_UDP_PAYLOAD-byte chunks and assigns each chunk a
   sequence number (0, 1, 2, …).
2. The sender may have up to ``window_size`` unacknowledged DATA packets in
   flight at the same time.
3. The receiver returns cumulative ACKs representing the next expected DATA
   sequence number.
4. On timeout without ACK progress, the sender retransmits the active window up
   to ``max_retries`` times.
5. After all DATA packets are cumulatively ACK-ed, a FIN packet is sent and a
   FIN_ACK is awaited.
6. Returns the SHA-256 hex digest of the file so the caller can send it over
   the control channel for end-to-end integrity verification.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from common.checksum import sha256_file
from common.constants import DEFAULT_UDP_WINDOW_SIZE, MAX_UDP_PAYLOAD, PacketFlag
from common.packet import PacketError, UDPPacket

ProgressCallback = Callable[[int, int], None]  # (bytes_sent, total_bytes)


def _progress_bar(sent: int, total: int) -> None:
    if total <= 0:
        return
    pct = sent / total
    filled = int(pct * 30)
    bar = "#" * filled + "-" * (30 - filled)
    sys.stderr.write(f"\r  [{bar}] {pct*100:5.1f}%  {sent:,}/{total:,} bytes  ")
    sys.stderr.flush()
    if sent >= total:
        sys.stderr.write("\n")
        sys.stderr.flush()


class TransferError(IOError):
    """Raised when the reliable UDP transfer fails permanently."""


class UDPSender:
    """Send a single file reliably over UDP using Go-Back-N ARQ.

    Parameters
    ----------
    sock:
        A *connected* UDP socket (``sock.connect((host, port))`` already called).
    transfer_id:
        Unique 32-bit integer identifying this transfer (e.g. port number or
        counter). Both sides must agree on the same value so multiplexed
        datagrams can be filtered.
    timeout_s:
        Per-window ACK wait timeout in seconds.
    max_retries:
        Maximum retransmit attempts before giving up.
    window_size:
        Maximum number of unacknowledged DATA packets allowed in flight.
    """
    count_ack = 0
    def __init__(
        self,
        sock: socket.socket,
        transfer_id: int,
        timeout_s: float = 0.5,
        max_retries: int = 10,
        window_size: int = DEFAULT_UDP_WINDOW_SIZE,
        progress: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self._sock = sock
        self._tid = transfer_id
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._window_size = max(1, window_size)
        self._progress = progress
        self._cancel_event = cancel_event
        self._sock.settimeout(timeout_s)

    def send_file(self, path: Path) -> str:
        """Transmit *path* and return its SHA-256 digest."""
        total = path.stat().st_size
        acked_bytes = 0
        base_seq = 0
        next_seq = 0
        retries_without_progress = 0
        eof = False
        in_flight: dict[int, tuple[bytes, int]] = {}
        cb = self._progress or _progress_bar

        with path.open("rb") as fh:
            while not eof or in_flight:
                self._raise_if_cancelled()

                while not eof and next_seq < base_seq + self._window_size:
                    chunk = fh.read(MAX_UDP_PAYLOAD)
                    if not chunk:
                        eof = True
                        break
                    packet = UDPPacket(PacketFlag.DATA, self._tid, sequence=next_seq, payload=chunk)
                    raw = packet.to_bytes()
                    self._sock.send(raw)
                    in_flight[next_seq] = (raw, len(chunk))
                    next_seq += 1

                if not in_flight:
                    continue

                ack_no = self._wait_for_cumulative_ack(base_seq, next_seq)
                
                if ack_no is None:
                    print("No ACK received, retransmitting window")
                    if retries_without_progress >= self._max_retries:
                        raise TransferError(
                            f"no ACK progress after {self._max_retries} retries for window starting at seq={base_seq}"
                        )
                    retries_without_progress += 1
                    for seq in range(base_seq, next_seq):
                        self.count_ack += 1
                        print(seq, self.count_ack)
                        self._raise_if_cancelled()
                        self._sock.send(in_flight[seq][0])
                    continue

                retries_without_progress = 0
                while base_seq < ack_no:
                    _raw, chunk_len = in_flight.pop(base_seq)
                    acked_bytes += chunk_len
                    base_seq += 1
                    cb(acked_bytes, total)

        self._send_fin(next_seq)
        return sha256_file(path)

    def _send_fin(self, seq: int) -> None:
        packet = UDPPacket(PacketFlag.FIN, self._tid, sequence=seq)
        raw = packet.to_bytes()
        for attempt in range(self._max_retries + 1):
            self._raise_if_cancelled()
            self._sock.send(raw)
            try:
                data = self._sock.recv(65535)
                reply = UDPPacket.from_bytes(data)
                if reply.transfer_id == self._tid and PacketFlag.FIN_ACK in reply.flags:
                    return
            except (socket.timeout, PacketError):
                pass
            if attempt == self._max_retries:
                raise TransferError("no FIN_ACK received")

    def _wait_for_cumulative_ack(self, base_seq: int, next_seq: int) -> int | None:
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            self._raise_if_cancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._sock.settimeout(remaining)
            try:
                data = self._sock.recv(65535)
                packet = UDPPacket.from_bytes(data)
            except socket.timeout:
                break
            except PacketError:
                continue

            if packet.transfer_id != self._tid:
                continue
            if PacketFlag.ACK not in packet.flags:
                continue
            if packet.acknowledgement <= base_seq:
                continue
            if packet.acknowledgement > next_seq:
                continue
            return packet.acknowledgement
        return None

    def _raise_if_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise TransferError("transfer cancelled")

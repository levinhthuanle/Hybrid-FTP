"""Reliable UDP sender — Stop-and-Wait with timeout/retransmit.

Protocol overview
-----------------
1. Sender reads file in MAX_UDP_PAYLOAD-byte chunks and assigns each chunk a
   sequence number (0, 1, 2, …).
2. Each chunk is wrapped in a UDPPacket (DATA flag) and sent over an already-
   connected UDP socket.
3. Sender waits up to ``timeout_s`` seconds for a matching ACK packet.
4. On timeout or NAK (wrong sequence), the same packet is retransmitted up to
   ``max_retries`` times.
5. After all DATA packets are ACK-ed, a FIN packet is sent and a FIN_ACK is
   awaited.
6. Returns the SHA-256 hex digest of the file so the caller can send it over
   the control channel for end-to-end integrity verification.
"""

from __future__ import annotations

import socket
import sys
import time
from pathlib import Path
from typing import Callable

from common.checksum import sha256_file
from common.constants import MAX_UDP_PAYLOAD, PacketFlag
from common.packet import UDPPacket, PacketError

ProgressCallback = Callable[[int, int], None]  # (bytes_sent, total_bytes)


def _progress_bar(sent: int, total: int) -> None:
    if total <= 0:
        return
    pct = sent / total
    filled = int(pct * 30)
    bar = "█" * filled + "░" * (30 - filled)
    sys.stderr.write(f"\r  [{bar}] {pct*100:5.1f}%  {sent:,}/{total:,} bytes  ")
    sys.stderr.flush()
    if sent >= total:
        sys.stderr.write("\n")
        sys.stderr.flush()


class TransferError(IOError):
    """Raised when the reliable UDP transfer fails permanently."""


class UDPSender:
    """Send a single file reliably over UDP using Stop-and-Wait ARQ.

    Parameters
    ----------
    sock:
        A *connected* UDP socket (``sock.connect((host, port))`` already called).
    transfer_id:
        Unique 32-bit integer identifying this transfer (e.g. port number or
        counter).  Both sides must agree on the same value so multiplexed
        datagrams can be filtered.
    timeout_s:
        Per-packet ACK wait timeout in seconds.
    max_retries:
        Maximum retransmit attempts before giving up.
    """

    def __init__(
        self,
        sock: socket.socket,
        transfer_id: int,
        timeout_s: float = 0.5,
        max_retries: int = 10,
        progress: ProgressCallback | None = None,
    ) -> None:
        self._sock = sock
        self._tid = transfer_id
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._progress = progress
        self._sock.settimeout(timeout_s)

    def send_file(self, path: Path) -> str:
        """Transmit *path* and return its SHA-256 digest."""
        total = path.stat().st_size
        sent = 0
        seq = 0
        cb = self._progress or _progress_bar
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(MAX_UDP_PAYLOAD)
                if not chunk:
                    break
                self._send_data(seq, chunk)
                sent += len(chunk)
                cb(sent, total)
                seq += 1
        self._send_fin(seq)
        return sha256_file(path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send_data(self, seq: int, payload: bytes) -> None:
        pkt = UDPPacket(PacketFlag.DATA, self._tid, sequence=seq, payload=payload)
        raw = pkt.to_bytes()
        for attempt in range(self._max_retries + 1):
            self._sock.send(raw)
            ack = self._wait_ack(seq)
            if ack:
                return
            if attempt < self._max_retries:
                continue
        raise TransferError(f"no ACK for seq={seq} after {self._max_retries} retries")

    def _send_fin(self, seq: int) -> None:
        pkt = UDPPacket(PacketFlag.FIN, self._tid, sequence=seq)
        raw = pkt.to_bytes()
        for attempt in range(self._max_retries + 1):
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

    def _wait_ack(self, expected_seq: int) -> bool:
        deadline = time.monotonic() + self._timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            self._sock.settimeout(remaining)
            try:
                data = self._sock.recv(65535)
                pkt = UDPPacket.from_bytes(data)
            except (socket.timeout, PacketError):
                break
            if pkt.transfer_id != self._tid:
                continue
            if PacketFlag.ACK in pkt.flags and pkt.acknowledgement == expected_seq:
                return True
        return False

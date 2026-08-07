"""Reliable UDP receiver — Go-Back-N receiver with cumulative ACKs.

Protocol overview
-----------------
1. Receiver listens on a bound UDP socket for DATA packets from the sender.
2. On receiving a well-formed DATA packet with the expected sequence number, the
   payload is written to the output file and a cumulative ACK is sent back.
3. Duplicate packets are ACK-ed again with the same cumulative ACK so the
   sender can advance or recover.
4. Out-of-order packets are dropped; the current cumulative ACK is resent to
   trigger a Go-Back-N retransmit from the sender.
5. When a FIN packet arrives, a FIN_ACK is sent and the function returns.
6. The SHA-256 digest of the assembled file is returned for integrity check.
"""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path
from typing import Callable

from common.checksum import sha256_file
from common.constants import DEFAULT_UDP_WINDOW_SIZE, PacketFlag
from common.packet import PacketError, UDPPacket

ProgressCallback = Callable[[int, int], None]  # (bytes_received, total_bytes)


def _progress_bar(received: int, total: int) -> None:
    if total <= 0:
        pct_str = "???"
        bar = "-" * 30
        sys.stderr.write(f"\r  [{bar}] {pct_str}  {received:,} bytes  ")
    else:
        pct = received / total
        filled = int(pct * 30)
        bar = "#" * filled + "-" * (30 - filled)
        sys.stderr.write(f"\r  [{bar}] {pct*100:5.1f}%  {received:,}/{total:,} bytes  ")
    sys.stderr.flush()
    if total > 0 and received >= total:
        sys.stderr.write("\n")
        sys.stderr.flush()


class TransferError(IOError):
    """Raised when the transfer cannot be completed."""


class UDPReceiver:
    """Receive a single file reliably over UDP using Go-Back-N semantics.

    Parameters
    ----------
    sock:
        A *bound* UDP socket. The receiver will call ``recvfrom`` on it so it
        learns the sender's address on the first packet.
    transfer_id:
        Must match the sender's transfer_id; packets with other IDs are ignored.
    timeout_s:
        How long to wait for the next packet before declaring the transfer
        timed-out.
    """

    def __init__(
        self,
        sock: socket.socket,
        transfer_id: int,
        timeout_s: float = 10.0,
        total_bytes: int = 0,
        window_size: int = DEFAULT_UDP_WINDOW_SIZE,
        progress: ProgressCallback | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None:
        self._sock = sock
        self._tid = transfer_id
        self._timeout = timeout_s
        self._total = total_bytes
        self._window_size = max(1, window_size)
        self._progress = progress
        self._cancel_event = cancel_event
        self._sock.settimeout(timeout_s)

    def receive_file(self, dest: Path) -> str:
        """Receive the incoming transfer and write it to *dest*.

        Returns the SHA-256 hex digest of the written file.
        """
        expected_seq = 0
        received = 0
        sender_addr: tuple[str, int] | None = None
        cb = self._progress or _progress_bar

        with dest.open("wb") as fh:
            while True:
                self._raise_if_cancelled()
                try:
                    raw, addr = self._sock.recvfrom(65535)
                except socket.timeout:
                    raise TransferError("receive timeout waiting for next packet")

                try:
                    packet = UDPPacket.from_bytes(raw)
                except PacketError:
                    continue

                if packet.transfer_id != self._tid:
                    continue

                if sender_addr is None:
                    sender_addr = addr

                if PacketFlag.FIN in packet.flags:
                    fin_ack = UDPPacket(
                        PacketFlag.FIN_ACK,
                        self._tid,
                        acknowledgement=packet.sequence,
                    )
                    self._sock.sendto(fin_ack.to_bytes(), sender_addr)
                    break

                if PacketFlag.DATA not in packet.flags:
                    continue

                if packet.sequence == expected_seq:
                    fh.write(packet.payload)
                    received += len(packet.payload)
                    cb(received, self._total)
                    expected_seq += 1

                ack = UDPPacket(
                    PacketFlag.ACK,
                    self._tid,
                    acknowledgement=expected_seq,
                )
                self._sock.sendto(ack.to_bytes(), sender_addr)

        if self._total <= 0:
            sys.stderr.write(f"\r  [{'#'*30}]  {received:,} bytes  \n")
            sys.stderr.flush()

        return sha256_file(dest)

    def _raise_if_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise TransferError("transfer cancelled")

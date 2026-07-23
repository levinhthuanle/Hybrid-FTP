"""Reliable UDP receiver — Stop-and-Wait ARQ, duplicate filtering, in-order assembly.

Protocol overview
-----------------
1. Receiver listens on a bound UDP socket for DATA packets from the sender.
2. On receiving a well-formed DATA packet with the expected sequence number, the
   payload is written to the output file and an ACK is sent back.
3. Duplicate packets (already-seen sequence number) are silently ACK-ed again so
   the sender can advance.
4. Out-of-order packets are dropped; the last ACK is resent to trigger a
   retransmit from the sender.
5. When a FIN packet arrives, a FIN_ACK is sent and the function returns.
6. The SHA-256 digest of the assembled file is returned for integrity check.
"""

from __future__ import annotations

import socket
from pathlib import Path

from common.checksum import sha256_file
from common.constants import PacketFlag
from common.packet import UDPPacket, PacketError


class TransferError(IOError):
    """Raised when the transfer cannot be completed."""


class UDPReceiver:
    """Receive a single file reliably over UDP using Stop-and-Wait ARQ.

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
    ) -> None:
        self._sock = sock
        self._tid = transfer_id
        self._timeout = timeout_s
        self._sock.settimeout(timeout_s)

    def receive_file(self, dest: Path) -> str:
        """Receive the incoming transfer and write it to *dest*.

        Returns the SHA-256 hex digest of the written file.

        Raises
        ------
        TransferError
            On timeout or unrecoverable protocol error.
        """
        expected_seq = 0
        sender_addr: tuple[str, int] | None = None

        with dest.open("wb") as fh:
            while True:
                try:
                    raw, addr = self._sock.recvfrom(65535)
                except socket.timeout:
                    raise TransferError("receive timeout waiting for next packet")

                try:
                    pkt = UDPPacket.from_bytes(raw)
                except PacketError:
                    # corrupted datagram — drop, sender will retransmit
                    continue

                if pkt.transfer_id != self._tid:
                    continue

                if sender_addr is None:
                    sender_addr = addr

                # FIN — transfer complete
                if PacketFlag.FIN in pkt.flags:
                    fin_ack = UDPPacket(
                        PacketFlag.FIN_ACK,
                        self._tid,
                        acknowledgement=pkt.sequence,
                    )
                    self._sock.sendto(fin_ack.to_bytes(), sender_addr)
                    break

                if PacketFlag.DATA not in pkt.flags:
                    continue

                if pkt.sequence == expected_seq:
                    fh.write(pkt.payload)
                    ack = UDPPacket(
                        PacketFlag.ACK,
                        self._tid,
                        acknowledgement=expected_seq,
                    )
                    self._sock.sendto(ack.to_bytes(), sender_addr)
                    expected_seq += 1
                else:
                    # duplicate or out-of-order — re-ACK last good seq
                    last_ack_seq = expected_seq - 1 if expected_seq > 0 else 0
                    ack = UDPPacket(
                        PacketFlag.ACK,
                        self._tid,
                        acknowledgement=last_ack_seq,
                    )
                    self._sock.sendto(ack.to_bytes(), sender_addr)

        return sha256_file(dest)

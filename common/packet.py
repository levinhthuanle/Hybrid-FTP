"""Binary packet codec for the custom reliable UDP protocol.

The checksum is calculated over the header with a zero checksum field followed by
the payload. This lets receivers detect corruption before acting on a packet.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .checksum import crc32
from .constants import MAX_UDP_PAYLOAD, UDP_MAGIC, UDP_VERSION, PacketFlag


class PacketError(ValueError):
    """Raised when a UDP datagram does not conform to the Hybrid FTP format."""


# magic(2), version(1), flags(1), transfer_id(4), sequence(4),
# acknowledgement(4), payload_length(2), checksum(4) = 22 bytes.
HEADER_FORMAT = "!2sBBIIIHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


@dataclass(frozen=True, slots=True)
class UDPPacket:
    """One reliable-UDP protocol unit.

    ``transfer_id`` distinguishes simultaneous transfers. Sequence and ACK
    numbers are zero-based and represent packet numbers, not byte offsets.
    """

    flags: PacketFlag
    transfer_id: int
    sequence: int = 0
    acknowledgement: int = 0
    payload: bytes = b""

    def __post_init__(self) -> None:
        for name, value in (
            ("transfer_id", self.transfer_id),
            ("sequence", self.sequence),
            ("acknowledgement", self.acknowledgement),
        ):
            if not 0 <= value <= 0xFFFFFFFF:
                raise PacketError(f"{name} must fit in an unsigned 32-bit integer")
        if len(self.payload) > MAX_UDP_PAYLOAD:
            raise PacketError(f"payload exceeds {MAX_UDP_PAYLOAD} bytes")

    def to_bytes(self) -> bytes:
        """Encode this packet, including its integrity checksum."""

        header_without_checksum = struct.pack(
            HEADER_FORMAT,
            UDP_MAGIC,
            UDP_VERSION,
            int(self.flags),
            self.transfer_id,
            self.sequence,
            self.acknowledgement,
            len(self.payload),
            0,
        )
        checksum = crc32(header_without_checksum + self.payload)
        header = header_without_checksum[:-4] + struct.pack("!I", checksum)
        return header + self.payload

    @classmethod
    def from_bytes(cls, datagram: bytes) -> "UDPPacket":
        """Validate and decode a received datagram."""

        if len(datagram) < HEADER_SIZE:
            raise PacketError("datagram is shorter than the UDP header")
        header = datagram[:HEADER_SIZE]
        magic, version, flags, transfer_id, sequence, acknowledgement, length, checksum = struct.unpack(
            HEADER_FORMAT, header
        )
        if magic != UDP_MAGIC:
            raise PacketError("unexpected UDP packet magic")
        if version != UDP_VERSION:
            raise PacketError(f"unsupported UDP packet version: {version}")
        payload = datagram[HEADER_SIZE:]
        if length != len(payload):
            raise PacketError("payload length does not match datagram length")
        if length > MAX_UDP_PAYLOAD:
            raise PacketError("payload exceeds configured maximum")
        header_without_checksum = header[:-4] + b"\x00\x00\x00\x00"
        if crc32(header_without_checksum + payload) != checksum:
            raise PacketError("UDP packet checksum verification failed")
        return cls(PacketFlag(flags), transfer_id, sequence, acknowledgement, payload)


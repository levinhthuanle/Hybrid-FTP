"""Constants shared by the control and data planes."""

from enum import IntFlag


ENCODING = "utf-8"
CONTROL_LINE_ENDING = "\r\n"

# A UDP datagram starts with this value so unrelated UDP traffic can be ignored.
UDP_MAGIC = b"HF"
UDP_VERSION = 1
MAX_UDP_PAYLOAD = 1_024
MAX_CONTROL_LINE = 4_096


class PacketFlag(IntFlag):
    """Flags used by the reliable-UDP packet header."""

    DATA = 0x01
    ACK = 0x02
    FIN = 0x04
    FIN_ACK = 0x08
    ERROR = 0x10


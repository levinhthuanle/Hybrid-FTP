import unittest

from common.constants import PacketFlag
from common.packet import PacketError, UDPPacket
from common.protocol import ReplyCode, format_reply, parse_command


class PacketTests(unittest.TestCase):
    def test_packet_round_trip(self) -> None:
        original = UDPPacket(PacketFlag.DATA, transfer_id=7, sequence=3, payload=b"hello")
        self.assertEqual(UDPPacket.from_bytes(original.to_bytes()), original)

    def test_corrupted_packet_is_rejected(self) -> None:
        encoded = bytearray(UDPPacket(PacketFlag.DATA, transfer_id=1, payload=b"hello").to_bytes())
        encoded[-1] ^= 1
        with self.assertRaises(PacketError):
            UDPPacket.from_bytes(bytes(encoded))


class ProtocolTests(unittest.TestCase):
    def test_command_and_reply(self) -> None:
        self.assertEqual(parse_command("stor report.pdf\r\n").name, "STOR")
        self.assertIsNone(parse_command("LIST").argument)
        self.assertEqual(format_reply(ReplyCode.COMMAND_OK, "OK"), b"200 OK\r\n")


if __name__ == "__main__":
    unittest.main()

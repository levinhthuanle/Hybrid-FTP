"""Focused tests for the custom reliable UDP transport behavior."""

from __future__ import annotations

import socket
import tempfile
import unittest
from pathlib import Path

from common.constants import DEFAULT_UDP_WINDOW_SIZE, MAX_UDP_PAYLOAD, PacketFlag
from common.packet import UDPPacket
from transport.udp_receiver import UDPReceiver
from transport.udp_sender import UDPSender


class AckLossSocket:
    """Fake connected UDP socket that drops the first DATA ACK."""

    def __init__(self, transfer_id: int) -> None:
        self.transfer_id = transfer_id
        self.sent_packets: list[UDPPacket] = []
        self.data_recv_calls = 0

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def send(self, data: bytes) -> int:
        self.sent_packets.append(UDPPacket.from_bytes(data))
        return len(data)

    def recv(self, size: int) -> bytes:
        last = self.sent_packets[-1]
        if PacketFlag.DATA in last.flags:
            self.data_recv_calls += 1
            if self.data_recv_calls == 1:
                raise socket.timeout
            return UDPPacket(
                PacketFlag.ACK,
                self.transfer_id,
                acknowledgement=last.sequence + 1,
            ).to_bytes()

        if PacketFlag.FIN in last.flags:
            return UDPPacket(
                PacketFlag.FIN_ACK,
                self.transfer_id,
                acknowledgement=last.sequence,
            ).to_bytes()

        raise socket.timeout


class DuplicateDataSocket:
    """Fake bound UDP socket that delivers duplicate DATA before FIN."""

    def __init__(self, transfer_id: int) -> None:
        self.addr = ("127.0.0.1", 9999)
        self.sent_acks: list[UDPPacket] = []
        self.datagrams = [
            UDPPacket(PacketFlag.DATA, transfer_id, sequence=0, payload=b"abc").to_bytes(),
            UDPPacket(PacketFlag.DATA, transfer_id, sequence=0, payload=b"abc").to_bytes(),
            UDPPacket(PacketFlag.DATA, transfer_id, sequence=1, payload=b"def").to_bytes(),
            UDPPacket(PacketFlag.FIN, transfer_id, sequence=2).to_bytes(),
        ]

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def recvfrom(self, size: int) -> tuple[bytes, tuple[str, int]]:
        if not self.datagrams:
            raise socket.timeout
        return self.datagrams.pop(0), self.addr

    def sendto(self, data: bytes, addr: tuple[str, int]) -> int:
        self.sent_acks.append(UDPPacket.from_bytes(data))
        return len(data)


class DataLossSocket(AckLossSocket):
    """Fake sender socket whose receiver drops the first DATA datagram."""

    def recv(self, size: int) -> bytes:
        last = self.sent_packets[-1]
        if PacketFlag.DATA in last.flags:
            self.data_recv_calls += 1
            if self.data_recv_calls == 1:
                raise socket.timeout
            return UDPPacket(
                PacketFlag.ACK,
                self.transfer_id,
                acknowledgement=last.sequence + 1,
            ).to_bytes()
        if PacketFlag.FIN in last.flags:
            return UDPPacket(
                PacketFlag.FIN_ACK,
                self.transfer_id,
                acknowledgement=last.sequence,
            ).to_bytes()
        raise socket.timeout


class FinLossSocket:
    """Fake sender socket whose receiver drops the first FIN datagram."""

    def __init__(self, transfer_id: int) -> None:
        self.transfer_id = transfer_id
        self.sent_packets: list[UDPPacket] = []
        self.fin_recv_calls = 0

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def send(self, data: bytes) -> int:
        self.sent_packets.append(UDPPacket.from_bytes(data))
        return len(data)

    def recv(self, size: int) -> bytes:
        last = self.sent_packets[-1]
        if PacketFlag.DATA in last.flags:
            return UDPPacket(
                PacketFlag.ACK,
                self.transfer_id,
                acknowledgement=last.sequence + 1,
            ).to_bytes()
        if PacketFlag.FIN in last.flags:
            self.fin_recv_calls += 1
            if self.fin_recv_calls == 1:
                raise socket.timeout
            return UDPPacket(
                PacketFlag.FIN_ACK,
                self.transfer_id,
                acknowledgement=last.sequence,
            ).to_bytes()
        raise socket.timeout


class OutOfOrderDataSocket(DuplicateDataSocket):
    """Fake bound socket that delivers seq=1 before seq=0."""

    def __init__(self, transfer_id: int) -> None:
        super().__init__(transfer_id)
        self.datagrams = [
            UDPPacket(PacketFlag.DATA, transfer_id, sequence=1, payload=b"def").to_bytes(),
            UDPPacket(PacketFlag.DATA, transfer_id, sequence=0, payload=b"abc").to_bytes(),
            UDPPacket(PacketFlag.DATA, transfer_id, sequence=1, payload=b"def").to_bytes(),
            UDPPacket(PacketFlag.FIN, transfer_id, sequence=2).to_bytes(),
        ]


class SlidingWindowSocket:
    """Fake connected UDP socket that ACKs a whole sender window at once."""

    def __init__(self, transfer_id: int) -> None:
        self.transfer_id = transfer_id
        self.sent_packets: list[UDPPacket] = []
        self.recv_calls = 0

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def send(self, data: bytes) -> int:
        self.sent_packets.append(UDPPacket.from_bytes(data))
        return len(data)

    def recv(self, size: int) -> bytes:
        last = self.sent_packets[-1]
        if PacketFlag.FIN in last.flags:
            return UDPPacket(
                PacketFlag.FIN_ACK,
                self.transfer_id,
                acknowledgement=last.sequence,
            ).to_bytes()

        self.recv_calls += 1
        if self.recv_calls == 1:
            return UDPPacket(
                PacketFlag.ACK,
                self.transfer_id,
                acknowledgement=3,
            ).to_bytes()

        highest_seq = max(
            pkt.sequence
            for pkt in self.sent_packets
            if PacketFlag.DATA in pkt.flags
        )
        return UDPPacket(
            PacketFlag.ACK,
            self.transfer_id,
            acknowledgement=highest_seq + 1,
        ).to_bytes()


class ReliableUDPBehaviorTests(unittest.TestCase):
    def test_transport_uses_configured_default_window_size(self) -> None:
        transfer_id = 41
        fake_socket = AckLossSocket(transfer_id)
        sender = UDPSender(fake_socket, transfer_id, progress=lambda _sent, _total: None)
        self.assertEqual(sender._window_size, DEFAULT_UDP_WINDOW_SIZE)

    def test_sender_retransmits_data_when_ack_is_lost(self) -> None:
        transfer_id = 42
        fake_socket = AckLossSocket(transfer_id)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"hello")
            UDPSender(
                fake_socket,
                transfer_id,
                timeout_s=0.01,
                max_retries=2,
                progress=lambda _sent, _total: None,
            ).send_file(path)

        data_packets = [p for p in fake_socket.sent_packets if PacketFlag.DATA in p.flags]
        self.assertEqual([p.sequence for p in data_packets], [0, 0])
        self.assertTrue(any(PacketFlag.FIN in p.flags for p in fake_socket.sent_packets))

    def test_receiver_acks_duplicate_data_without_duplicate_write(self) -> None:
        transfer_id = 7
        fake_socket = DuplicateDataSocket(transfer_id)

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "received.bin"
            UDPReceiver(
                fake_socket,
                transfer_id,
                timeout_s=0.01,
                progress=lambda _received, _total: None,
            ).receive_file(dest)
            self.assertEqual(dest.read_bytes(), b"abcdef")

        ack_packets = [p for p in fake_socket.sent_acks if PacketFlag.ACK in p.flags]
        self.assertEqual([p.acknowledgement for p in ack_packets], [1, 1, 2])
        self.assertTrue(any(PacketFlag.FIN_ACK in p.flags for p in fake_socket.sent_acks))

    def test_sender_retransmits_when_data_is_dropped(self) -> None:
        transfer_id = 9
        fake_socket = DataLossSocket(transfer_id)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"lost once")
            UDPSender(
                fake_socket,
                transfer_id,
                timeout_s=0.01,
                max_retries=2,
                progress=lambda _sent, _total: None,
            ).send_file(path)
        data_packets = [p for p in fake_socket.sent_packets if PacketFlag.DATA in p.flags]
        self.assertEqual([p.sequence for p in data_packets], [0, 0])

    def test_receiver_recovers_after_out_of_order_data(self) -> None:
        transfer_id = 10
        fake_socket = OutOfOrderDataSocket(transfer_id)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "received.bin"
            UDPReceiver(
                fake_socket,
                transfer_id,
                timeout_s=0.01,
                progress=lambda _received, _total: None,
            ).receive_file(dest)
            self.assertEqual(dest.read_bytes(), b"abcdef")
        ack_packets = [p for p in fake_socket.sent_acks if PacketFlag.ACK in p.flags]
        self.assertEqual([p.acknowledgement for p in ack_packets], [0, 1, 2])

    def test_sender_retransmits_fin_when_fin_is_dropped(self) -> None:
        transfer_id = 11
        fake_socket = FinLossSocket(transfer_id)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"fin retry")
            UDPSender(
                fake_socket,
                transfer_id,
                timeout_s=0.01,
                max_retries=2,
                progress=lambda _sent, _total: None,
            ).send_file(path)
        fin_packets = [p for p in fake_socket.sent_packets if PacketFlag.FIN in p.flags]
        self.assertEqual([p.sequence for p in fin_packets], [1, 1])

    def test_sender_pipelines_multiple_packets_with_sliding_window(self) -> None:
        transfer_id = 13
        fake_socket = SlidingWindowSocket(transfer_id)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"A" * (MAX_UDP_PAYLOAD * 4))
            UDPSender(
                fake_socket,
                transfer_id,
                timeout_s=0.01,
                max_retries=2,
                window_size=3,
                progress=lambda _sent, _total: None,
            ).send_file(path)

        data_packets = [p for p in fake_socket.sent_packets if PacketFlag.DATA in p.flags]
        self.assertEqual([p.sequence for p in data_packets[:3]], [0, 1, 2])


if __name__ == "__main__":
    unittest.main()

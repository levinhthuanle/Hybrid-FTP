"""Integration tests for UDP file transfer (RETR / STOR / STOU / APPE).

Each test spins up a real FTPServer on a random port, connects with
FTPClient, and performs actual UDP transfers — verifying SHA-256 digests
end-to-end.
"""

from __future__ import annotations

import hashlib
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from common.config import ClientConfig, ServerConfig
from common.checksum import sha256_file
from server import FTPServer
from client.ftp_client import FTPClient, FTPError


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TransferTestBase(unittest.TestCase):
    """Start server + client pair with isolated temp dirs."""

    def setUp(self) -> None:
        self._storage = tempfile.TemporaryDirectory()
        self._downloads = tempfile.TemporaryDirectory()

        port = _free_port()
        self._srv_cfg = ServerConfig(
            host="127.0.0.1",
            control_port=port,
            storage_root=Path(self._storage.name),
            udp_timeout_seconds=0.5,
            udp_max_retries=10,
        )
        self._server = FTPServer(self._srv_cfg)
        self._thread = threading.Thread(target=self._server.start, daemon=True)
        self._thread.start()
        time.sleep(0.05)

        self._cli_cfg = ClientConfig(host="127.0.0.1", control_port=port,
                                     download_root=Path(self._downloads.name))
        self._client = FTPClient(self._cli_cfg)
        self._client.connect()
        self._client.login("admin", "1234")

    def tearDown(self) -> None:
        try:
            self._client.quit()
        except Exception:
            self._client.close()
        self._server.stop()
        self._storage.cleanup()
        self._downloads.cleanup()

    def _make_file(self, name: str, content: bytes) -> Path:
        p = Path(self._storage.name) / name
        p.write_bytes(content)
        return p

    def _upload_file(self, name: str, content: bytes) -> Path:
        """Write file to a temp upload dir and upload it via client."""
        with tempfile.TemporaryDirectory() as upload_dir:
            local = Path(upload_dir) / name
            local.write_bytes(content)
            self._client.upload(local, name)
        return Path(self._storage.name) / name


# ------------------------------------------------------------------
# STOR — upload
# ------------------------------------------------------------------

class UploadTests(TransferTestBase):

    def test_upload_small_text(self) -> None:
        content = b"Hello Hybrid FTP!\n"
        stored = self._upload_file("hello.txt", content)
        self.assertTrue(stored.exists())
        self.assertEqual(stored.read_bytes(), content)

    def test_upload_digest_matches(self) -> None:
        content = b"checksum test content"
        expected = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            local = Path(d) / "check.txt"
            local.write_bytes(content)
            digest = self._client.upload(local, "check.txt")
        self.assertEqual(digest, expected)

    def test_upload_binary_file(self) -> None:
        # 5 KB of pseudo-binary data
        content = bytes(range(256)) * 20
        stored = self._upload_file("binary.bin", content)
        self.assertEqual(stored.read_bytes(), content)

    def test_upload_multi_packet(self) -> None:
        # > 1024 bytes forces multiple UDP packets
        content = b"X" * 4096
        stored = self._upload_file("big.txt", content)
        self.assertEqual(stored.read_bytes(), content)

    def test_upload_exact_packet_boundary(self) -> None:
        # exactly 1024 bytes = one full packet
        content = b"A" * 1024
        stored = self._upload_file("boundary.bin", content)
        self.assertEqual(stored.read_bytes(), content)

    def test_upload_empty_file(self) -> None:
        stored = self._upload_file("empty.txt", b"")
        self.assertTrue(stored.exists())
        self.assertEqual(stored.read_bytes(), b"")

    def test_upload_overwrites_existing(self) -> None:
        self._make_file("overwrite.txt", b"old content")
        stored = self._upload_file("overwrite.txt", b"new content")
        self.assertEqual(stored.read_bytes(), b"new content")


# ------------------------------------------------------------------
# RETR — download
# ------------------------------------------------------------------

class DownloadTests(TransferTestBase):

    def test_download_small_text(self) -> None:
        content = b"download me\n"
        self._make_file("dl.txt", content)
        dest = Path(self._downloads.name) / "dl.txt"
        self._client.download("dl.txt", dest)
        self.assertEqual(dest.read_bytes(), content)

    def test_download_digest_matches(self) -> None:
        content = b"integrity check"
        expected = hashlib.sha256(content).hexdigest()
        self._make_file("integrity.txt", content)
        dest = Path(self._downloads.name) / "integrity.txt"
        digest = self._client.download("integrity.txt", dest)
        self.assertEqual(digest, expected)

    def test_download_binary_file(self) -> None:
        content = bytes(range(256)) * 15
        self._make_file("img.bin", content)
        dest = Path(self._downloads.name) / "img.bin"
        self._client.download("img.bin", dest)
        self.assertEqual(dest.read_bytes(), content)

    def test_download_multi_packet(self) -> None:
        content = b"Y" * 5000
        self._make_file("multi.bin", content)
        dest = Path(self._downloads.name) / "multi.bin"
        self._client.download("multi.bin", dest)
        self.assertEqual(dest.read_bytes(), content)

    def test_download_nonexistent_returns_550(self) -> None:
        dest = Path(self._downloads.name) / "ghost.txt"
        with self.assertRaises(FTPError) as ctx:
            self._client.download("ghost.txt", dest)
        self.assertEqual(ctx.exception.code, 550)

    def test_download_preserves_binary_exactly(self) -> None:
        # all 256 byte values — verifies no newline or encoding corruption
        content = bytes(range(256))
        self._make_file("allbytes.bin", content)
        dest = Path(self._downloads.name) / "allbytes.bin"
        self._client.download("allbytes.bin", dest)
        self.assertEqual(dest.read_bytes(), content)


# ------------------------------------------------------------------
# Round-trip — upload then download, compare
# ------------------------------------------------------------------

class RoundTripTests(TransferTestBase):

    def _roundtrip(self, content: bytes, name: str) -> None:
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / name
            src.write_bytes(content)
            upload_digest = self._client.upload(src, name)

        dest = Path(self._downloads.name) / name
        download_digest = self._client.download(name, dest)

        self.assertEqual(upload_digest, download_digest)
        self.assertEqual(dest.read_bytes(), content)

    def test_roundtrip_text(self) -> None:
        self._roundtrip(b"Hello, round-trip!\n", "rt_text.txt")

    def test_roundtrip_binary(self) -> None:
        self._roundtrip(bytes(range(256)) * 10, "rt_binary.bin")

    def test_roundtrip_large(self) -> None:
        # ~50 KB — 50 packets
        self._roundtrip(b"Z" * 51200, "rt_large.bin")

    def test_roundtrip_exact_boundary(self) -> None:
        self._roundtrip(b"B" * 2048, "rt_boundary.bin")  # exactly 2 packets

    def test_roundtrip_one_byte(self) -> None:
        self._roundtrip(b"\xff", "rt_one.bin")


# ------------------------------------------------------------------
# STOU — upload with unique name
# ------------------------------------------------------------------

class StouTests(TransferTestBase):

    def _stou(self, content: bytes, hint: str) -> None:
        data_sock = self._client._open_pasv_data()
        code, msg = self._client._cmd(f"STOU {hint}")
        if code != 150:
            data_sock.close()
            raise FTPError(code, msg)
        from transport.udp_sender import UDPSender
        udp_port, tid = FTPClient._parse_udp_params(msg)
        import socket as _s
        udp = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
        udp.connect(("127.0.0.1", udp_port))
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(content)
            tmp = Path(tf.name)
        try:
            UDPSender(udp, tid).send_file(tmp)
        finally:
            udp.close()
            data_sock.close()
            tmp.unlink()
        code, _ = self._client._read_reply()
        self.assertEqual(code, 226)

    def test_stou_creates_file(self) -> None:
        self._stou(b"unique content", "stou.txt")
        names = [p.name for p in Path(self._storage.name).iterdir()]
        self.assertTrue(any("stou" in n for n in names))

    def test_stou_no_overwrite(self) -> None:
        self._stou(b"first", "dup.txt")
        self._stou(b"second", "dup.txt")
        files = list(Path(self._storage.name).iterdir())
        self.assertEqual(len(files), 2)


# ------------------------------------------------------------------
# APPE — append
# ------------------------------------------------------------------

class AppendTests(TransferTestBase):

    def _appe(self, content: bytes, name: str) -> None:
        data_sock = self._client._open_pasv_data()
        code, msg = self._client._cmd(f"APPE {name}")
        if code != 150:
            data_sock.close()
            raise FTPError(code, msg)
        from transport.udp_sender import UDPSender
        udp_port, tid = FTPClient._parse_udp_params(msg)
        import socket as _s
        udp = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
        udp.connect(("127.0.0.1", udp_port))
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(content)
            tmp = Path(tf.name)
        try:
            UDPSender(udp, tid).send_file(tmp)
        finally:
            udp.close()
            data_sock.close()
            tmp.unlink()
        code, _ = self._client._read_reply()
        self.assertEqual(code, 226)

    def test_appe_to_existing(self) -> None:
        self._make_file("log.txt", b"line1\n")
        self._appe(b"line2\n", "log.txt")
        result = (Path(self._storage.name) / "log.txt").read_bytes()
        self.assertEqual(result, b"line1\nline2\n")

    def test_appe_creates_new_file(self) -> None:
        self._appe(b"brand new\n", "newlog.txt")
        result = (Path(self._storage.name) / "newlog.txt").read_bytes()
        self.assertEqual(result, b"brand new\n")


class ActiveAndAbortTests(TransferTestBase):

    def test_active_mode_upload_and_download(self) -> None:
        content = bytes(range(256)) * 8
        with tempfile.TemporaryDirectory() as upload_dir:
            source = Path(upload_dir) / "active.bin"
            source.write_bytes(content)
            upload_digest = self._client.upload_active(source, "active.bin")
        destination = Path(self._downloads.name) / "active.bin"
        download_digest = self._client.download_active("active.bin", destination)
        self.assertEqual(upload_digest, download_digest)
        self.assertEqual(destination.read_bytes(), content)

    def test_abor_cancels_waiting_upload_without_creating_target(self) -> None:
        data_sock = self._client._open_pasv_data()
        code, _ = self._client._cmd("STOR aborted.bin")
        self.assertEqual(code, 150)
        code, _ = self._client._cmd("ABOR")
        self.assertEqual(code, 426)
        data_sock.close()
        time.sleep(0.05)
        self.assertFalse((Path(self._storage.name) / "aborted.bin").exists())
        code, _ = self._client._cmd("NOOP")
        self.assertEqual(code, 200)


class SlidingWindowTransferTests(TransferTestBase):

    def setUp(self) -> None:
        self._storage = tempfile.TemporaryDirectory()
        self._downloads = tempfile.TemporaryDirectory()

        port = _free_port()
        self._srv_cfg = ServerConfig(
            host="127.0.0.1",
            control_port=port,
            storage_root=Path(self._storage.name),
            udp_timeout_seconds=0.5,
            udp_max_retries=10,
            udp_window_size=3,
        )
        self._server = FTPServer(self._srv_cfg)
        self._thread = threading.Thread(target=self._server.start, daemon=True)
        self._thread.start()
        time.sleep(0.05)

        self._cli_cfg = ClientConfig(
            host="127.0.0.1",
            control_port=port,
            download_root=Path(self._downloads.name),
            udp_window_size=3,
        )
        self._client = FTPClient(self._cli_cfg)
        self._client.connect()
        self._client.login("admin", "1234")

    def test_roundtrip_with_window_size_three(self) -> None:
        content = bytes(range(256)) * 16
        with tempfile.TemporaryDirectory() as upload_dir:
            source = Path(upload_dir) / "window3.bin"
            source.write_bytes(content)
            upload_digest = self._client.upload(source, "window3.bin")

        destination = Path(self._downloads.name) / "window3.bin"
        download_digest = self._client.download("window3.bin", destination)
        self.assertEqual(upload_digest, download_digest)
        self.assertEqual(destination.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()

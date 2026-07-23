"""Integration tests for the TCP control server.

Each test spins up a real FTPServer on a random port in a background thread,
connects with a raw socket, and exchanges FTP commands over the wire.
"""

from __future__ import annotations

import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path

from common.config import ServerConfig
from server import FTPServer


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FTPClient:
    """Minimal raw FTP client for testing."""

    def __init__(self, host: str, port: int) -> None:
        self._sock = socket.create_connection((host, port), timeout=5)
        self._buf = b""

    def readline(self) -> str:
        while b"\r\n" not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("server closed connection")
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\r\n")
        return line.decode("utf-8")

    def send(self, line: str) -> None:
        self._sock.sendall((line + "\r\n").encode("utf-8"))

    def cmd(self, line: str) -> str:
        """Send a command and return the first response line."""
        self.send(line)
        return self.readline()

    def code(self, line: str) -> int:
        """Send a command and return just the numeric reply code."""
        return int(self.cmd(line).split()[0])

    def close(self) -> None:
        self._sock.close()


class ServerTestBase(unittest.TestCase):
    """Start a fresh server with a temp storage dir for each test."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        port = _find_free_port()
        self._config = ServerConfig(
            host="127.0.0.1",
            control_port=port,
            storage_root=Path(self._tmpdir.name),
        )
        self._server = FTPServer(self._config)
        self._thread = threading.Thread(target=self._server.start, daemon=True)
        self._thread.start()
        time.sleep(0.05)  # wait for bind

    def tearDown(self) -> None:
        self._server.stop()
        self._tmpdir.cleanup()

    def connect(self) -> FTPClient:
        c = FTPClient("127.0.0.1", self._config.control_port)
        greeting = c.readline()
        self.assertTrue(greeting.startswith("220"), f"Expected 220 greeting, got: {greeting}")
        return c

    def login(self, client: FTPClient, user: str = "admin", password: str = "1234") -> None:
        self.assertEqual(client.code(f"USER {user}"), 331)
        self.assertEqual(client.code(f"PASS {password}"), 230)


# ------------------------------------------------------------------
# Auth tests
# ------------------------------------------------------------------

class AuthTests(ServerTestBase):

    def test_greeting(self) -> None:
        c = self.connect()
        c.close()

    def test_login_success(self) -> None:
        c = self.connect()
        self.login(c)
        c.close()

    def test_login_wrong_password(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("USER admin"), 331)
        self.assertEqual(c.code("PASS wrong"), 530)
        c.close()

    def test_login_unknown_user(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("USER nobody"), 331)
        self.assertEqual(c.code("PASS anything"), 530)
        c.close()

    def test_command_blocked_before_login(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("PWD"), 530)
        c.close()

    def test_noop_allowed_before_login(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("NOOP"), 200)
        c.close()

    def test_pass_without_user(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("PASS 1234"), 503)
        c.close()

    def test_quit(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("QUIT"), 221)
        c.close()

    def test_anonymous_login(self) -> None:
        c = self.connect()
        self.assertEqual(c.code("USER anonymous"), 331)
        self.assertEqual(c.code("PASS "), 230)
        c.close()


# ------------------------------------------------------------------
# Directory tests
# ------------------------------------------------------------------

class DirectoryTests(ServerTestBase):

    def test_pwd_root(self) -> None:
        c = self.connect()
        self.login(c)
        reply = c.cmd("PWD")
        self.assertTrue(reply.startswith("257"))
        self.assertIn("/", reply)
        c.close()

    def test_mkd_and_cwd(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("MKD mydir"), 257)
        self.assertEqual(c.code("CWD mydir"), 250)
        reply = c.cmd("PWD")
        self.assertIn("mydir", reply)
        c.close()

    def test_cdup(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("MKD subdir"), 257)
        self.assertEqual(c.code("CWD subdir"), 250)
        self.assertEqual(c.code("CDUP"), 250)
        reply = c.cmd("PWD")
        self.assertIn("/", reply)
        c.close()

    def test_rmd(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("MKD deleteme"), 257)
        self.assertEqual(c.code("RMD deleteme"), 250)
        c.close()

    def test_cwd_nonexistent(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("CWD doesnotexist"), 550)
        c.close()

    def test_path_traversal_blocked(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertIn(c.code("CWD ../../etc"), (550, 550))
        c.close()

    def test_unknown_command(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("XFOO bar"), 502)
        c.close()


# ------------------------------------------------------------------
# Transfer setup tests
# ------------------------------------------------------------------

class TransferSetupTests(ServerTestBase):

    def test_type_ascii(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("TYPE A"), 200)
        c.close()

    def test_type_binary(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("TYPE I"), 200)
        c.close()

    def test_type_invalid(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("TYPE Z"), 501)
        c.close()

    def test_mode_stream(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("MODE S"), 200)
        c.close()

    def test_pasv(self) -> None:
        c = self.connect()
        self.login(c)
        reply = c.cmd("PASV")
        self.assertTrue(reply.startswith("227"), f"Expected 227, got: {reply}")
        c.close()

    def test_port(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("PORT 127,0,0,1,19,136"), 200)
        c.close()

    def test_port_invalid(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("PORT bad"), 501)
        c.close()


# ------------------------------------------------------------------
# LIST / NLST via PASV
# ------------------------------------------------------------------

class ListTests(ServerTestBase):

    def _pasv_connect(self, client: FTPClient) -> socket.socket:
        """Issue PASV and return a connected data socket."""
        reply = client.cmd("PASV")
        # parse 227 Entering Passive Mode (h1,h2,h3,h4,p1,p2)
        nums = reply[reply.index("(") + 1 : reply.index(")")].split(",")
        host = ".".join(nums[:4])
        port = int(nums[4]) * 256 + int(nums[5])
        data_sock = socket.create_connection((host, port), timeout=5)
        return data_sock

    def test_list_empty_dir(self) -> None:
        c = self.connect()
        self.login(c)
        data = self._pasv_connect(c)
        reply = c.cmd("LIST")
        self.assertTrue(reply.startswith("150"), reply)
        listing = data.recv(4096).decode()
        data.close()
        done = c.readline()
        self.assertTrue(done.startswith("226"), done)
        self.assertEqual(listing, "")
        c.close()

    def test_list_shows_created_dir(self) -> None:
        c = self.connect()
        self.login(c)
        c.code("MKD visible")
        data = self._pasv_connect(c)
        c.send("LIST")
        c.readline()  # 150
        listing = data.recv(4096).decode()
        data.close()
        c.readline()  # 226
        self.assertIn("visible", listing)
        c.close()

    def test_nlst(self) -> None:
        c = self.connect()
        self.login(c)
        c.code("MKD alpha")
        c.code("MKD beta")
        data = self._pasv_connect(c)
        c.send("NLST")
        c.readline()  # 150
        listing = data.recv(4096).decode()
        data.close()
        c.readline()  # 226
        self.assertIn("alpha", listing)
        self.assertIn("beta", listing)
        c.close()


# ------------------------------------------------------------------
# File operation tests
# ------------------------------------------------------------------

class FileOpsTests(ServerTestBase):

    def _create_file(self, name: str, content: str = "hello") -> None:
        (Path(self._tmpdir.name) / name).write_text(content)

    def test_size(self) -> None:
        self._create_file("sample.txt", "hello")
        c = self.connect()
        self.login(c)
        reply = c.cmd("SIZE sample.txt")
        self.assertTrue(reply.startswith("213"), reply)
        self.assertIn("5", reply)
        c.close()

    def test_mdtm(self) -> None:
        self._create_file("sample.txt")
        c = self.connect()
        self.login(c)
        reply = c.cmd("MDTM sample.txt")
        self.assertTrue(reply.startswith("213"), reply)
        # Format: 20260723... (14 digits)
        digits = reply.split()[1]
        self.assertEqual(len(digits), 14)
        self.assertTrue(digits.isdigit())
        c.close()

    def test_hash(self) -> None:
        self._create_file("sample.txt", "hello")
        c = self.connect()
        self.login(c)
        reply = c.cmd("HASH sample.txt")
        self.assertTrue(reply.startswith("213"), reply)
        self.assertIn("SHA-256", reply)
        c.close()

    def test_dele(self) -> None:
        self._create_file("todelete.txt")
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("DELE todelete.txt"), 250)
        self.assertFalse((Path(self._tmpdir.name) / "todelete.txt").exists())
        c.close()

    def test_dele_nonexistent(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("DELE ghost.txt"), 550)
        c.close()

    def test_rnfr_rnto(self) -> None:
        self._create_file("old.txt")
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("RNFR old.txt"), 350)
        self.assertEqual(c.code("RNTO new.txt"), 250)
        self.assertFalse((Path(self._tmpdir.name) / "old.txt").exists())
        self.assertTrue((Path(self._tmpdir.name) / "new.txt").exists())
        c.close()

    def test_rnto_without_rnfr(self) -> None:
        c = self.connect()
        self.login(c)
        self.assertEqual(c.code("RNTO new.txt"), 503)
        c.close()

    def test_help(self) -> None:
        c = self.connect()
        self.login(c)
        reply = c.cmd("HELP")
        self.assertTrue(reply.startswith("214"), reply)
        c.close()


# ------------------------------------------------------------------
# Concurrency test
# ------------------------------------------------------------------

class ConcurrencyTests(ServerTestBase):

    def test_two_clients_isolated(self) -> None:
        c1 = self.connect()
        c2 = self.connect()
        self.login(c1)
        self.login(c2)

        # c1 creates a dir
        self.assertEqual(c1.code("MKD client1dir"), 257)
        # c2's cwd should still be /
        reply = c2.cmd("PWD")
        self.assertNotIn("client1dir", reply)

        c1.close()
        c2.close()


if __name__ == "__main__":
    unittest.main()

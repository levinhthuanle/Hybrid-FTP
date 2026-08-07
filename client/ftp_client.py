"""TCP control-channel client for Hybrid FTP.

Wraps a raw TCP socket and exposes typed methods for every FTP command.
All data-channel coordination (PASV/PORT, UDP transfer port negotiation)
is handled here so command_handler.py can stay at a high level.
"""

from __future__ import annotations

import socket
from pathlib import Path

from common.config import ClientConfig
from common.constants import ENCODING


class FTPError(Exception):
    """Raised when the server replies with an unexpected or error code."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(f"{code} {message}")
        self.code = code
        self.message = message


class FTPClient:
    """One TCP control connection to a Hybrid FTP server.

    Usage
    -----
    ::
        client = FTPClient()
        client.connect()
        client.login("admin", "1234")
        client.upload(Path("file.txt"), "file.txt")
        client.download("file.txt", Path("file.txt"))
        client.quit()
    """

    def __init__(
        self,
        config: ClientConfig | None = None,
        *,
        trace_control: bool = False,
    ) -> None:
        """Create a client.

        Set ``trace_control`` for an interactive CLI session to show the
        control-channel commands and exact FTP replies returned by the server.
        It remains disabled by default for library consumers and tests.
        """
        self._cfg = config or ClientConfig()
        self._sock: socket.socket | None = None
        self._buf = b""
        self._trace_control = trace_control

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> str:
        """Connect and return the 220 greeting text."""
        self._sock = socket.create_connection(
            (self._cfg.host, self._cfg.control_port), timeout=10
        )
        code, msg = self._read_reply()
        if code != 220:
            raise FTPError(code, msg)
        return msg

    def quit(self) -> None:
        self._cmd("QUIT")
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def close(self) -> None:
        """Close without sending QUIT (use after unexpected errors)."""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def user(self, username: str) -> None:
        """Send USER <username> and require the 331 intermediate reply."""
        code, msg = self._cmd(f"USER {username}")
        if code != 331:
            raise FTPError(code, msg)

    def pass_(self, password: str) -> None:
        """Send PASS <password> and require the 230 completion reply."""
        code, msg = self._cmd(f"PASS {password}")
        if code != 230:
            raise FTPError(code, msg)

    def login(self, username: str, password: str) -> None:
        """Convenience API that sends USER followed by PASS."""
        self.user(username)
        self.pass_(password)

    # ------------------------------------------------------------------
    # Directory navigation
    # ------------------------------------------------------------------

    def pwd(self) -> str:
        code, msg = self._cmd("PWD")
        if code != 257:
            raise FTPError(code, msg)
        # strip surrounding quotes if present
        if '"' in msg:
            return msg.split('"')[1]
        return msg

    def cwd(self, path: str) -> None:
        code, msg = self._cmd(f"CWD {path}")
        if code != 250:
            raise FTPError(code, msg)

    def cdup(self) -> None:
        code, msg = self._cmd("CDUP")
        if code != 250:
            raise FTPError(code, msg)

    def mkd(self, name: str) -> None:
        code, msg = self._cmd(f"MKD {name}")
        if code != 257:
            raise FTPError(code, msg)

    def rmd(self, name: str) -> None:
        code, msg = self._cmd(f"RMD {name}")
        if code != 250:
            raise FTPError(code, msg)

    def list(self, path: str = "") -> list[str]:
        """Return LIST output lines (ls -l style)."""
        return self._transfer_list(f"LIST{' ' + path if path else ''}")

    def nlst(self, path: str = "") -> list[str]:
        """Return NLST output lines (filenames only)."""
        return self._transfer_list(f"NLST{' ' + path if path else ''}")

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def size(self, filename: str) -> int:
        code, msg = self._cmd(f"SIZE {filename}")
        if code != 213:
            raise FTPError(code, msg)
        return int(msg.strip())

    def mdtm(self, filename: str) -> str:
        code, msg = self._cmd(f"MDTM {filename}")
        if code != 213:
            raise FTPError(code, msg)
        return msg.strip()

    def hash(self, filename: str) -> str:
        """Return the SHA-256 hex digest reported by the server."""
        code, msg = self._cmd(f"HASH {filename}")
        if code != 213:
            raise FTPError(code, msg)
        # format: "SHA-256 <digest> <filename>"
        parts = msg.strip().split()
        return parts[1] if len(parts) >= 2 else msg.strip()

    def stat(self, path: str = "") -> str:
        code, msg = self._cmd(f"STAT{' ' + path if path else ''}")
        return msg

    # ------------------------------------------------------------------
    # Transfer type / mode
    # ------------------------------------------------------------------

    def set_type(self, type_code: str) -> None:
        code, msg = self._cmd(f"TYPE {type_code.upper()}")
        if code != 200:
            raise FTPError(code, msg)

    def set_mode(self, mode_code: str) -> None:
        code, msg = self._cmd(f"MODE {mode_code.upper()}")
        if code != 200:
            raise FTPError(code, msg)

    def port(self, endpoint: str) -> None:
        code, msg = self._cmd(f"PORT {endpoint}")
        if code != 200:
            raise FTPError(code, msg)

    def pasv(self) -> str:
        code, msg = self._cmd("PASV")
        if code != 227:
            raise FTPError(code, msg)
        return msg

    def noop(self) -> None:
        code, msg = self._cmd("NOOP")
        if code != 200:
            raise FTPError(code, msg)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def dele(self, filename: str) -> None:
        code, msg = self._cmd(f"DELE {filename}")
        if code != 250:
            raise FTPError(code, msg)

    def rnfr(self, old: str) -> None:
        code, msg = self._cmd(f"RNFR {old}")
        if code != 350:
            raise FTPError(code, msg)

    def rnto(self, new: str) -> None:
        code, msg = self._cmd(f"RNTO {new}")
        if code != 250:
            raise FTPError(code, msg)

    def rename(self, old: str, new: str) -> None:
        """Convenience API that sends RNFR followed by RNTO."""
        self.rnfr(old)
        self.rnto(new)

    def abor(self) -> str:
        code, msg = self._cmd("ABOR")
        if code not in (226, 426):
            raise FTPError(code, msg)
        return msg

    def help(self, command: str | None = None) -> str:
        command_line = f"HELP {command}" if command else "HELP"
        code, msg = self._cmd(command_line)
        if code != 214:
            raise FTPError(code, msg)
        return msg

    # ------------------------------------------------------------------
    # UDP file transfer
    # ------------------------------------------------------------------

    def upload(self, local_path: Path, remote_name: str) -> str:
        """Backward-compatible API for STOR <remote_name>."""
        return self.stor(local_path, remote_name)

    def stor(self, local_path: Path, remote_name: str) -> str:
        """Upload *local_path* by sending STOR <remote_name>."""
        return self._upload_file(local_path, f"STOR {remote_name}")

    def stou(self, local_path: Path) -> str:
        """Upload *local_path* by sending the argument-free STOU command."""
        return self._upload_file(local_path, "STOU")

    def appe(self, local_path: Path, remote_name: str) -> str:
        """Append *local_path* by sending APPE <remote_name>."""
        return self._upload_file(local_path, f"APPE {remote_name}")

    def _upload_file(self, local_path: Path, command_line: str) -> str:
        """Send one FTP upload control command and stream its UDP payload."""
        from transport.udp_sender import UDPSender, TransferError

        if not local_path.is_file():
            raise FTPError(0, f"Local file unavailable: {local_path}")

        data_sock = self._open_pasv_data()
        code, msg = self._cmd(command_line)
        if code != 150:
            data_sock.close()
            raise FTPError(code, msg)

        udp_port, tid = self._parse_udp_params(msg)
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.connect((self._cfg.host, udp_port))
        try:
            sender = UDPSender(
                udp_sock,
                tid,
                window_size=self._cfg.udp_window_size,
            )
            digest = sender.send_file(local_path)
        except TransferError as exc:
            raise FTPError(0, str(exc)) from exc
        finally:
            udp_sock.close()
            data_sock.close()

        code, msg = self._read_reply()
        if code != 226:
            raise FTPError(code, msg)
        return self._verify_transfer_digest(digest, msg)
    def download(self, remote_name: str, local_path: Path) -> str:
        """Download *remote_name* from the server to *local_path*.

        Returns the SHA-256 digest confirmed by the server.
        """
        from transport.udp_receiver import UDPReceiver, TransferError

        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            total_bytes = self.size(remote_name)
        except FTPError:
            total_bytes = 0

        data_sock = self._open_pasv_data()
        code, msg = self._cmd(f"RETR {remote_name}")
        if code != 150:
            data_sock.close()
            raise FTPError(code, msg)

        udp_port, tid = self._parse_udp_params(msg)

        # bind client UDP socket and tell server our port via data socket
        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_sock.bind((self._local_bind_host(), 0))
        _, my_udp_port = udp_sock.getsockname()
        data_sock.sendall(f"{my_udp_port}\n".encode())

        try:
            receiver = UDPReceiver(
                udp_sock,
                tid,
                total_bytes=total_bytes,
                window_size=self._cfg.udp_window_size,
            )
            digest = receiver.receive_file(local_path)
        except TransferError as exc:
            raise FTPError(0, str(exc)) from exc
        finally:
            udp_sock.close()
            data_sock.close()

        code, msg = self._read_reply()
        if code != 226:
            raise FTPError(code, msg)
        return self._verify_transfer_digest(digest, msg)

    # ------------------------------------------------------------------
    def upload_active(self, local_path: Path, remote_name: str, listener: socket.socket | None = None) -> str:
        """Upload with active-mode TCP data setup and reliable UDP payloads."""
        from transport.udp_sender import UDPSender, TransferError
        if listener is None:
            listener = self._open_active_listener()
        data_sock: socket.socket | None = None
        udp_sock: socket.socket | None = None
        try:
            code, msg = self._cmd(f"STOR {remote_name}")
            if code != 150:
                raise FTPError(code, msg)
            data_sock = self._accept_active_data(listener)
            listener = None
            udp_port, tid = self._parse_udp_params(msg)
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.connect((self._cfg.host, udp_port))
            digest = UDPSender(
                udp_sock,
                tid,
                window_size=self._cfg.udp_window_size,
            ).send_file(local_path)
        except TransferError as exc:
            raise FTPError(0, str(exc)) from exc
        finally:
            if udp_sock is not None:
                udp_sock.close()
            if data_sock is not None:
                data_sock.close()
            if listener is not None:
                listener.close()
        code, msg = self._read_reply()
        if code != 226:
            raise FTPError(code, msg)
        return self._verify_transfer_digest(digest, msg)

    def download_active(self, remote_name: str, local_path: Path, listener: socket.socket | None = None) -> str:
        """Download with active-mode TCP data setup and reliable UDP payloads."""
        from transport.udp_receiver import UDPReceiver, TransferError
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            total_bytes = self.size(remote_name)
        except FTPError:
            total_bytes = 0
        if listener is None:
            listener = self._open_active_listener()
        data_sock: socket.socket | None = None
        udp_sock: socket.socket | None = None
        try:
            code, msg = self._cmd(f"RETR {remote_name}")
            if code != 150:
                raise FTPError(code, msg)
            data_sock = self._accept_active_data(listener)
            listener = None
            udp_port, tid = self._parse_udp_params(msg)
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.bind((self._local_bind_host(), 0))
            _, my_udp_port = udp_sock.getsockname()
            data_sock.sendall(f"{my_udp_port}\n".encode())
            digest = UDPReceiver(
                udp_sock,
                tid,
                total_bytes=total_bytes,
                window_size=self._cfg.udp_window_size,
            ).receive_file(local_path)
        except TransferError as exc:
            raise FTPError(0, str(exc)) from exc
        finally:
            if udp_sock is not None:
                udp_sock.close()
            if data_sock is not None:
                data_sock.close()
            if listener is not None:
                listener.close()
        code, msg = self._read_reply()
        if code != 226:
            raise FTPError(code, msg)
        return self._verify_transfer_digest(digest, msg)

    # Internal helpers
    # ------------------------------------------------------------------

    def _cmd(self, line: str) -> tuple[int, str]:
        """Send *line* and return (code, message)."""
        if self._trace_control:
            display_line = "PASS ******" if line.startswith("PASS ") else line
            print(f"--> {display_line}")
        self._sock.sendall((line + "\r\n").encode(ENCODING))
        return self._read_reply()

    def _read_reply(self) -> tuple[int, str]:
        """Read one (possibly multi-line) FTP reply and return (code, last_line)."""
        lines = []
        while True:
            line = self._readline()
            lines.append(line)
            if len(line) >= 4 and line[3] == " ":
                # standard single-line or last line of multi-line reply
                break
            if len(line) >= 4 and line[3] == "-":
                continue
        last = lines[-1]
        if self._trace_control:
            for reply_line in lines:
                print(f"<-- {reply_line}")
        code = int(last[:3])
        message = last[4:]
        return code, message

    def _readline(self) -> str:
        while b"\r\n" not in self._buf:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("server closed connection")
            self._buf += chunk
        line, _, self._buf = self._buf.partition(b"\r\n")
        return line.decode(ENCODING, errors="replace")

    def _open_pasv_data(self) -> socket.socket:
        """Issue PASV and return a connected TCP data socket."""
        code, msg = self._cmd("PASV")
        if code != 227:
            raise FTPError(code, msg)
        start = msg.index("(") + 1
        end = msg.index(")")
        nums = msg[start:end].split(",")
        host = ".".join(nums[:4])
        port = int(nums[4]) * 256 + int(nums[5])
        return socket.create_connection((host, port), timeout=10)

    def _open_active_listener(self, endpoint: str | None = None) -> socket.socket:
        """Listen locally, advertise PORT, and return the pending data listener.

        If *endpoint* is provided, bind the listener to the exact host/port tuple
        encoded as ``h1,h2,h3,h4,p1,p2`` so a prior ``PORT`` command can be used
        for a later active transfer.
        """
        if endpoint is None:
            bind_host = self._local_bind_host()
            bind_port = 0
        else:
            try:
                parts = [int(part) for part in endpoint.split(",")]
                if len(parts) != 6 or any(not 0 <= part <= 255 for part in parts):
                    raise ValueError
                bind_host = ".".join(str(part) for part in parts[:4])
                bind_port = parts[4] * 256 + parts[5]
                if bind_port == 0:
                    raise ValueError
            except ValueError as exc:
                raise FTPError(501, "Invalid PORT endpoint") from exc
        try:
            octets = [int(part) for part in bind_host.split(".")]
            if len(octets) != 4 or any(not 0 <= octet <= 255 for octet in octets):
                raise ValueError
        except ValueError as exc:
            raise FTPError(501, "Active mode requires an IPv4 client host") from exc
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((bind_host, bind_port))
        listener.listen(1)
        listener.settimeout(10)
        _, port = listener.getsockname()
        p1, p2 = port >> 8, port & 0xFF
        endpoint = ",".join([*(str(octet) for octet in octets), str(p1), str(p2)])
        code, msg = self._cmd(f"PORT {endpoint}")
        if code != 200:
            listener.close()
            raise FTPError(code, msg)
        return listener

    def _local_bind_host(self) -> str:
        """Return the client's local IPv4 address for inbound data sockets."""
        if self._sock is None:
            return "127.0.0.1"
        local_host = self._sock.getsockname()[0]
        return local_host if local_host not in {"0.0.0.0", "::"} else "127.0.0.1"

    @staticmethod
    def _accept_active_data(listener: socket.socket) -> socket.socket:
        try:
            conn, _ = listener.accept()
            return conn
        finally:
            listener.close()

    @staticmethod
    def _verify_transfer_digest(local_digest: str, reply_msg: str) -> str:
        marker = "SHA-256="
        if marker not in reply_msg:
            raise FTPError(226, "Server transfer reply did not include a SHA-256 digest")
        server_digest = reply_msg.split(marker, 1)[1].split()[0]
        if server_digest != local_digest:
            raise FTPError(426, "SHA-256 mismatch after transfer")
        return local_digest

    def _transfer_list(self, cmd_line: str) -> list[str]:
        """Open PASV data connection, send cmd_line, return lines received."""
        data_sock = self._open_pasv_data()
        code, msg = self._cmd(cmd_line)
        if code not in (125, 150):
            data_sock.close()
            raise FTPError(code, msg)
        raw = b""
        while True:
            chunk = data_sock.recv(4096)
            if not chunk:
                break
            raw += chunk
        data_sock.close()
        # read trailing 226
        code, msg = self._read_reply()
        if code != 226:
            raise FTPError(code, msg)
        text = raw.decode(ENCODING, errors="replace")
        return [l for l in text.splitlines() if l]

    @staticmethod
    def _parse_udp_params(reply_msg: str) -> tuple[int, int]:
        """Extract port and tid from server 150 reply.

        Expected format: "... port=<N> tid=<M> ..."
        """
        port = tid = None
        for token in reply_msg.split():
            if token.startswith("port="):
                port = int(token.split("=", 1)[1])
            elif token.startswith("tid="):
                tid = int(token.split("=", 1)[1])
        if port is None or tid is None:
            raise FTPError(150, f"Cannot parse UDP params from: {reply_msg!r}")
        return port, tid

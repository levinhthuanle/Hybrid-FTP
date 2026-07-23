"""Per-client FTP session: state machine and command handlers."""

from __future__ import annotations

import socket
import threading
from enum import Enum, auto
from pathlib import Path
from typing import Callable

from common.config import ServerConfig
from common.constants import CONTROL_LINE_ENDING, ENCODING, MAX_CONTROL_LINE
from common.protocol import Command, ReplyCode, format_reply, parse_command
from transport.udp_sender import UDPSender, TransferError as SenderError
from transport.udp_receiver import UDPReceiver, TransferError as ReceiverError

from .auth import username_exists, verify
from .file_manager import FileManager, PathError


class AuthState(Enum):
    NOT_LOGGED_IN = auto()
    USERNAME_GIVEN = auto()
    LOGGED_IN = auto()


class DataMode(Enum):
    ACTIVE = auto()
    PASSIVE = auto()


class TransferType(Enum):
    ASCII = "A"
    BINARY = "I"


# Commands allowed before login
_PREAUTH_COMMANDS = frozenset({"USER", "PASS", "QUIT", "HELP", "NOOP"})


class ClientSession:
    def __init__(
        self,
        conn: socket.socket,
        addr: tuple[str, int],
        config: ServerConfig,
        log_fn: Callable[[str], None],
    ) -> None:
        self._conn = conn
        self._addr = addr
        self._config = config
        self._log = log_fn

        self._auth_state = AuthState.NOT_LOGGED_IN
        self._pending_username: str | None = None
        self._username: str | None = None

        self._fm = FileManager(config.storage_root)
        self._cwd = Path("/")

        self._transfer_type = TransferType.BINARY
        self._data_mode: DataMode | None = None
        self._active_host: str | None = None
        self._active_port: int | None = None
        self._pasv_sock: socket.socket | None = None

        self._rnfr_path: Path | None = None
        self._abort = threading.Event()

        self._transfer_id_counter = 0

        self._handlers: dict[str, Callable[[Command], None]] = self._build_dispatch()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._send(ReplyCode.SERVICE_READY, f"Hybrid FTP Server ready")
        try:
            while True:
                line = self._readline()
                if line is None:
                    break
                try:
                    cmd = parse_command(line)
                except ValueError as exc:
                    self._send(ReplyCode.SYNTAX_ERROR, str(exc))
                    continue
                if not self._dispatch(cmd):
                    break
        finally:
            self._close_pasv_listener()

    def _readline(self) -> str | None:
        buf = bytearray()
        try:
            while True:
                ch = self._conn.recv(1)
                if not ch:
                    return None
                buf.extend(ch)
                if len(buf) > MAX_CONTROL_LINE:
                    self._send(ReplyCode.SYNTAX_ERROR, "Command line too long")
                    return None
                if buf.endswith(b"\r\n"):
                    return buf[:-2].decode(ENCODING, errors="replace")
        except OSError:
            return None

    def _send(self, code: ReplyCode | int, message: str) -> None:
        self._log(f"[{self._addr[0]}:{self._addr[1]}] >> {int(code)} {message}")
        try:
            self._conn.sendall(format_reply(code, message))
        except OSError:
            pass

    def _send_multiline(self, code: ReplyCode | int, lines: list[str]) -> None:
        """Send a multi-line FTP reply: first line uses '-', last uses ' '."""
        c = int(code)
        if not lines:
            self._send(code, "")
            return
        if len(lines) == 1:
            self._send(code, lines[0])
            return
        parts = [f"{c}-{lines[0]}{CONTROL_LINE_ENDING}"]
        for line in lines[1:-1]:
            parts.append(f" {line}{CONTROL_LINE_ENDING}")
        parts.append(f"{c} {lines[-1]}{CONTROL_LINE_ENDING}")
        payload = "".join(parts).encode(ENCODING)
        try:
            self._conn.sendall(payload)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _build_dispatch(self) -> dict[str, Callable[[Command], None]]:
        return {
            "USER": self._cmd_user,
            "PASS": self._cmd_pass,
            "QUIT": self._cmd_quit,
            "NOOP": self._cmd_noop,
            "PWD":  self._cmd_pwd,
            "CWD":  self._cmd_cwd,
            "CDUP": self._cmd_cdup,
            "MKD":  self._cmd_mkd,
            "RMD":  self._cmd_rmd,
            "LIST": self._cmd_list,
            "NLST": self._cmd_nlst,
            "STAT": self._cmd_stat,
            "SIZE": self._cmd_size,
            "MDTM": self._cmd_mdtm,
            "HASH": self._cmd_hash,
            "TYPE": self._cmd_type,
            "MODE": self._cmd_mode,
            "PORT": self._cmd_port,
            "PASV": self._cmd_pasv,
            "RETR": self._cmd_retr,
            "STOR": self._cmd_stor,
            "STOU": self._cmd_stou,
            "APPE": self._cmd_appe,
            "DELE": self._cmd_dele,
            "RNFR": self._cmd_rnfr,
            "RNTO": self._cmd_rnto,
            "ABOR": self._cmd_abor,
            "HELP": self._cmd_help,
        }

    def _dispatch(self, cmd: Command) -> bool:
        self._log(f"[{self._addr[0]}:{self._addr[1]}] << {cmd.name}{' ' + cmd.argument if cmd.argument else ''}")
        handler = self._handlers.get(cmd.name)
        if handler is None:
            self._send(ReplyCode.COMMAND_NOT_IMPLEMENTED, f"{cmd.name} not implemented")
            return True
        if cmd.name not in _PREAUTH_COMMANDS and self._auth_state != AuthState.LOGGED_IN:
            self._send(ReplyCode.NOT_LOGGED_IN, "Please login with USER and PASS")
            return True
        handler(cmd)
        return cmd.name != "QUIT"

    # ------------------------------------------------------------------
    # Auth commands
    # ------------------------------------------------------------------

    def _cmd_user(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Username required")
            return
        self._pending_username = cmd.argument
        self._auth_state = AuthState.USERNAME_GIVEN
        self._username = None
        if username_exists(cmd.argument):
            self._send(ReplyCode.USERNAME_OK, "Password required")
        else:
            # Still move to USERNAME_GIVEN; PASS will reject with 530
            self._send(ReplyCode.USERNAME_OK, "Password required")

    def _cmd_pass(self, cmd: Command) -> None:
        if self._auth_state != AuthState.USERNAME_GIVEN:
            self._send(503, "Login with USER first")
            return
        password = cmd.argument or ""
        if verify(self._pending_username, password):
            self._username = self._pending_username
            self._auth_state = AuthState.LOGGED_IN
            self._send(ReplyCode.LOGIN_SUCCESSFUL, f"Logged in as {self._username}")
        else:
            self._auth_state = AuthState.NOT_LOGGED_IN
            self._pending_username = None
            self._send(ReplyCode.NOT_LOGGED_IN, "Login incorrect")

    def _cmd_quit(self, cmd: Command) -> None:
        self._send(ReplyCode.GOODBYE, "Goodbye")

    def _cmd_noop(self, cmd: Command) -> None:
        self._send(ReplyCode.COMMAND_OK, "OK")

    # ------------------------------------------------------------------
    # Directory commands
    # ------------------------------------------------------------------

    def _cmd_pwd(self, cmd: Command) -> None:
        self._send(257, f'"{self._fm.to_virtual(self._real_cwd())}" is current directory')

    def _cmd_cwd(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Path required")
            return
        try:
            new_real = self._fm.change_dir(self._cwd, cmd.argument)
        except (FileNotFoundError, NotADirectoryError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._cwd = Path(self._fm.to_virtual(new_real))
        self._send(ReplyCode.FILE_ACTION_OK, f'Directory changed to "{self._fm.to_virtual(new_real)}"')

    def _cmd_cdup(self, cmd: Command) -> None:
        parent = str(self._cwd.parent) if str(self._cwd) != "/" else "/"
        self._cmd_cwd(Command("CDUP", parent))

    def _cmd_mkd(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Directory name required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            self._fm.make_dir(path)
        except (FileExistsError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._send(257, f'"{cmd.argument}" directory created')

    def _cmd_rmd(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Directory name required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            self._fm.remove_dir(path)
        except (FileNotFoundError, OSError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._send(ReplyCode.FILE_ACTION_OK, "Directory removed")

    def _cmd_list(self, cmd: Command) -> None:
        target = cmd.argument or str(self._cwd)
        try:
            path = self._fm.resolve(target, self._cwd)
            if not path.is_dir():
                path = path.parent
            lines = self._fm.list_dir(path)
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        data_sock = self._open_data_connection()
        if data_sock is None:
            return
        self._send(ReplyCode.OPENING_DATA_CONNECTION, "Here comes the directory listing")
        try:
            payload = "\r\n".join(lines) + ("\r\n" if lines else "")
            data_sock.sendall(payload.encode(ENCODING))
        finally:
            data_sock.close()
        self._send(ReplyCode.TRANSFER_COMPLETE, "Directory send OK")

    def _cmd_nlst(self, cmd: Command) -> None:
        target = cmd.argument or str(self._cwd)
        try:
            path = self._fm.resolve(target, self._cwd)
            if not path.is_dir():
                path = path.parent
            names = self._fm.nlst_dir(path)
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        data_sock = self._open_data_connection()
        if data_sock is None:
            return
        self._send(ReplyCode.OPENING_DATA_CONNECTION, "Here comes the name list")
        try:
            payload = "\r\n".join(names) + ("\r\n" if names else "")
            data_sock.sendall(payload.encode(ENCODING))
        finally:
            data_sock.close()
        self._send(ReplyCode.TRANSFER_COMPLETE, "Name list sent")

    def _cmd_stat(self, cmd: Command) -> None:
        if cmd.argument:
            try:
                path = self._fm.resolve(cmd.argument, self._cwd)
                info = f"{cmd.argument}: size={self._fm.file_size(path)} modified={self._fm.file_mdtm(path)}"
            except (FileNotFoundError, PathError) as exc:
                self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
                return
            self._send(213, info)
        else:
            cwd_str = self._fm.to_virtual(self._real_cwd())
            self._send(211, f"Connected as {self._username}, CWD={cwd_str}")

    # ------------------------------------------------------------------
    # File metadata commands
    # ------------------------------------------------------------------

    def _cmd_size(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            self._send(213, str(self._fm.file_size(path)))
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))

    def _cmd_mdtm(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            self._send(213, self._fm.file_mdtm(path))
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))

    def _cmd_hash(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            digest = self._fm.file_hash(path)
            self._send(213, f"SHA-256 {digest} {cmd.argument}")
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))

    # ------------------------------------------------------------------
    # Transfer setup commands
    # ------------------------------------------------------------------

    def _cmd_type(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Type code required (A or I)")
            return
        code = cmd.argument.upper()
        if code == "A":
            self._transfer_type = TransferType.ASCII
            self._send(ReplyCode.COMMAND_OK, "Switching to ASCII mode")
        elif code == "I":
            self._transfer_type = TransferType.BINARY
            self._send(ReplyCode.COMMAND_OK, "Switching to Binary mode")
        else:
            self._send(ReplyCode.PARAMETER_ERROR, f"Unknown type: {cmd.argument!r}")

    def _cmd_mode(self, cmd: Command) -> None:
        if cmd.argument and cmd.argument.upper() == "S":
            self._send(ReplyCode.COMMAND_OK, "Mode set to Stream")
        else:
            self._send(ReplyCode.COMMAND_NOT_IMPLEMENTED, "Only Stream mode (S) supported")

    def _cmd_port(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "PORT argument required")
            return
        try:
            parts = [int(x) for x in cmd.argument.split(",")]
            if len(parts) != 6:
                raise ValueError
            host = ".".join(str(p) for p in parts[:4])
            port = parts[4] * 256 + parts[5]
        except (ValueError, IndexError):
            self._send(ReplyCode.PARAMETER_ERROR, "Invalid PORT argument")
            return
        self._close_pasv_listener()
        self._active_host = host
        self._active_port = port
        self._data_mode = DataMode.ACTIVE
        self._send(ReplyCode.COMMAND_OK, f"PORT command successful ({host}:{port})")

    def _cmd_pasv(self, cmd: Command) -> None:
        self._close_pasv_listener()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self._config.host, 0))
        sock.listen(1)
        _, port = sock.getsockname()
        self._pasv_sock = sock
        self._data_mode = DataMode.PASSIVE
        h = self._config.host.replace(".", ",")
        p1, p2 = port >> 8, port & 0xFF
        self._send(227, f"Entering Passive Mode ({h},{p1},{p2})")

    # ------------------------------------------------------------------
    # Transfer commands (stubs — RDT layer fills these in Phase 2)
    # ------------------------------------------------------------------

    def _cmd_retr(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            if not path.is_file():
                raise FileNotFoundError(cmd.argument)
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        data_sock = self._open_data_connection()
        if data_sock is None:
            return
        udp_sock, udp_port = self._open_udp_socket()
        tid = self._next_transfer_id()
        self._send(ReplyCode.OPENING_DATA_CONNECTION,
                   f"Opening UDP data connection port={udp_port} tid={tid} for {cmd.argument}")
        try:
            sender = UDPSender(udp_sock, tid,
                               timeout_s=self._config.udp_timeout_seconds,
                               max_retries=self._config.udp_max_retries)
            digest = sender.send_file(path)
            self._send(ReplyCode.TRANSFER_COMPLETE, f"Transfer complete SHA-256={digest}")
        except SenderError as exc:
            self._send(ReplyCode.TRANSFER_ABORTED, f"Transfer failed: {exc}")
        finally:
            udp_sock.close()
            data_sock.close()

    def _cmd_stor(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
        except PathError as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._do_receive(path)

    def _cmd_stou(self, cmd: Command) -> None:
        real_cwd = self._real_cwd()
        basename = cmd.argument or "file"
        path = self._fm.unique_path(real_cwd, basename)
        self._do_receive(path)

    def _cmd_appe(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
        except PathError as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._do_receive(path, append=True)

    # ------------------------------------------------------------------
    # File operation commands
    # ------------------------------------------------------------------

    def _cmd_dele(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            self._fm.delete_file(path)
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._send(ReplyCode.FILE_ACTION_OK, "File deleted")

    def _cmd_rnfr(self, cmd: Command) -> None:
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "Filename required")
            return
        try:
            path = self._fm.resolve(cmd.argument, self._cwd)
            if not path.exists():
                raise FileNotFoundError(cmd.argument)
        except (FileNotFoundError, PathError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        self._rnfr_path = path
        self._send(ReplyCode.RENAME_PENDING, "Ready for RNTO")

    def _cmd_rnto(self, cmd: Command) -> None:
        if self._rnfr_path is None:
            self._send(503, "RNFR required before RNTO")
            return
        if not cmd.argument:
            self._send(ReplyCode.PARAMETER_ERROR, "New name required")
            return
        try:
            dst = self._fm.resolve(cmd.argument, self._cwd)
            self._fm.rename(self._rnfr_path, dst)
        except (FileNotFoundError, PathError, OSError) as exc:
            self._send(ReplyCode.FILE_UNAVAILABLE, str(exc))
            return
        finally:
            self._rnfr_path = None
        self._send(ReplyCode.FILE_ACTION_OK, "Rename successful")

    def _cmd_abor(self, cmd: Command) -> None:
        self._abort.set()
        self._send(ReplyCode.TRANSFER_ABORTED, "Abort requested")

    def _cmd_help(self, cmd: Command) -> None:
        commands = sorted(self._handlers.keys())
        self._send_multiline(214, ["Available commands:"] + [" ".join(commands[i:i+8]) for i in range(0, len(commands), 8)])

    # ------------------------------------------------------------------
    # Data connection helpers
    # ------------------------------------------------------------------

    def _open_data_connection(self) -> socket.socket | None:
        if self._data_mode == DataMode.ACTIVE:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((self._active_host, self._active_port))
                return sock
            except OSError as exc:
                self._send(ReplyCode.CANNOT_OPEN_DATA_CONNECTION, f"Cannot connect: {exc}")
                return None
        elif self._data_mode == DataMode.PASSIVE:
            try:
                self._pasv_sock.settimeout(30)
                conn, _ = self._pasv_sock.accept()
                self._close_pasv_listener()
                return conn
            except OSError as exc:
                self._send(ReplyCode.CANNOT_OPEN_DATA_CONNECTION, f"Accept failed: {exc}")
                return None
        else:
            self._send(ReplyCode.CANNOT_OPEN_DATA_CONNECTION, "Use PORT or PASV first")
            return None

    def _close_pasv_listener(self) -> None:
        if self._pasv_sock is not None:
            try:
                self._pasv_sock.close()
            except OSError:
                pass
            self._pasv_sock = None
        self._data_mode = None

    def _real_cwd(self) -> Path:
        """Return the real filesystem path for the current virtual cwd."""
        return self._fm.resolve(str(self._cwd), Path("/"))

    # ------------------------------------------------------------------
    # UDP transfer helpers
    # ------------------------------------------------------------------

    def _next_transfer_id(self) -> int:
        self._transfer_id_counter = (self._transfer_id_counter + 1) & 0xFFFFFFFF
        return self._transfer_id_counter

    def _open_udp_socket(self) -> tuple[socket.socket, int]:
        """Bind a UDP socket on a free port and return (sock, port)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self._config.host, 0))
        _, port = sock.getsockname()
        return sock, port

    def _do_receive(self, path: Path, append: bool = False) -> None:
        """Open data connection, receive file via UDP, report digest."""
        data_sock = self._open_data_connection()
        if data_sock is None:
            return
        udp_sock, udp_port = self._open_udp_socket()
        tid = self._next_transfer_id()
        mode = "append" if append else "store"
        self._send(ReplyCode.OPENING_DATA_CONNECTION,
                   f"Opening UDP data connection port={udp_port} tid={tid} ready to {mode} {path.name}")
        try:
            receiver = UDPReceiver(udp_sock, tid,
                                   timeout_s=max(self._config.udp_timeout_seconds * 20, 10.0))
            dest = path if not append else self._append_dest(path)
            digest = receiver.receive_file(dest)
            if append and dest != path:
                # merge temp file into target
                with path.open("ab") as dst, dest.open("rb") as src:
                    dst.write(src.read())
                dest.unlink()
            self._send(ReplyCode.TRANSFER_COMPLETE, f"Transfer complete SHA-256={digest}")
        except ReceiverError as exc:
            self._send(ReplyCode.TRANSFER_ABORTED, f"Transfer failed: {exc}")
        finally:
            udp_sock.close()
            data_sock.close()

    def _append_dest(self, path: Path) -> Path:
        """Return a temp path for receiving append data."""
        return self._fm.unique_path(path.parent, f"_append_{path.name}")

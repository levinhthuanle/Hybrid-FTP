"""Interactive CLI that sends the approved FTP control-command syntax."""

from __future__ import annotations

import shlex
import sys
import socket
from pathlib import Path

from common.config import ClientConfig
from .ftp_client import FTPClient, FTPError


HELP_TEXT = """\
Connection:
  CONNECT [host [port]]          Connect to the server (default: 127.0.0.1:2121)

FTP control commands:
  USER <username>                Begin authentication
  PASS <password>                Complete authentication
  QUIT                            End the session
  NOOP                            Keep-alive ping
  PWD                             Print the remote working directory
  CWD <path>                     Change remote directory
  CDUP                            Move to the parent directory
  MKD <dirname>                  Create a directory
  RMD <dirname>                  Remove an empty directory
  LIST [path]                    Detailed directory listing
  NLST [path]                    Filename-only listing
  STAT [path]                    Server or file status
  SIZE <filename>                File size
  MDTM <filename>                Last modification time
  TYPE {A | I}                   ASCII or binary transfer type
  MODE {S | B | C}               Transfer mode (the server supports S)
  PORT <h1,h2,h3,h4,p1,p2>       Configure active mode
  PASV                            Configure passive mode
  RETR <filename>                Download to client/download/<filename>
  STOR <filename>                Upload client/upload/<filename>
  STOU <local-file>              CLI source selector; sends FTP STOU
  APPE <local-file> <filename>   CLI source selector; sends FTP APPE <filename>
  DELE <filename>                Delete a remote file
  RNFR <oldname>                 Begin a rename operation
  RNTO <newname>                 Complete the pending rename operation
  HASH <filename>                Return the remote SHA-256 digest
  ABOR                            Abort the active transfer
  HELP [command]                 Show command help

The arguments marked as "CLI source selector" identify a local file only;
the control command sent to the server still has the exact FTP syntax above.
"""


class CLI:
    def __init__(self) -> None:
        self._client: FTPClient | None = None
        self._upload_root = Path("client/upload")
        self._download_root = Path("client/download")
        self._active_listener: socket.socket | None = None
        self._upload_root.mkdir(parents=True, exist_ok=True)
        self._download_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        print("Hybrid FTP Client. Type 'HELP' for commands.")
        while True:
            try:
                line = input("ftp> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self._safe_quit()
                break
            if not line:
                continue
            try:
                parts = shlex.split(line)
            except ValueError as exc:
                print(f"Syntax error: {exc}")
                continue
            if not parts:
                continue
            cmd, args = parts[0].upper(), parts[1:]
            try:
                self._dispatch(cmd, args)
            except FTPError as exc:
                print(f"Error: {exc}")
            except Exception as exc:
                print(f"Unexpected error: {exc}")

    def _dispatch(self, cmd: str, args: list[str]) -> None:
        match cmd:
            case "CONNECT":
                self._do_connect(args)
            case "USER":
                if not self._require_exact_args(args, 1, "USER <username>"):
                    return
                self._require_connection()
                self._client.user(args[0])
                print("Username accepted; send PASS <password>.")
            case "PASS":
                if not self._require_exact_args(args, 1, "PASS <password>"):
                    return
                self._require_connection()
                self._client.pass_(args[0])
                print("Login successful.")
            case "QUIT":
                if not self._require_exact_args(args, 0, "QUIT"):
                    return
                self._safe_quit()
                sys.exit(0)
            case "NOOP":
                if not self._require_exact_args(args, 0, "NOOP"):
                    return
                self._require_connection()
                self._client.noop()
                print("OK")
            case "PWD":
                if not self._require_exact_args(args, 0, "PWD"):
                    return
                self._require_connection()
                print(self._client.pwd())
            case "CWD":
                if not self._require_exact_args(args, 1, "CWD <path>"):
                    return
                self._require_connection()
                self._client.cwd(args[0])
                print(self._client.pwd())
            case "CDUP":
                if not self._require_exact_args(args, 0, "CDUP"):
                    return
                self._require_connection()
                self._client.cdup()
                print(self._client.pwd())
            case "MKD":
                if not self._require_exact_args(args, 1, "MKD <dirname>"):
                    return
                self._require_connection()
                self._client.mkd(args[0])
                print(f"Directory '{args[0]}' created.")
            case "RMD":
                if not self._require_exact_args(args, 1, "RMD <dirname>"):
                    return
                self._require_connection()
                self._client.rmd(args[0])
                print(f"Directory '{args[0]}' removed.")
            case "LIST":
                if not self._require_at_most_args(args, 1, "LIST [path]"):
                    return
                self._require_connection()
                lines = self._client.list(args[0] if args else "")
                print("\n".join(lines) if lines else "(empty)")
            case "NLST":
                if not self._require_at_most_args(args, 1, "NLST [path]"):
                    return
                self._require_connection()
                lines = self._client.nlst(args[0] if args else "")
                print("\n".join(lines) if lines else "(empty)")
            case "STAT":
                if not self._require_at_most_args(args, 1, "STAT [path]"):
                    return
                self._require_connection()
                print(self._client.stat(args[0] if args else ""))
            case "SIZE":
                if not self._require_exact_args(args, 1, "SIZE <filename>"):
                    return
                self._require_connection()
                print(f"{self._client.size(args[0])} bytes")
            case "MDTM":
                if not self._require_exact_args(args, 1, "MDTM <filename>"):
                    return
                self._require_connection()
                print(self._client.mdtm(args[0]))
            case "TYPE":
                if not self._require_exact_args(args, 1, "TYPE {A | I}"):
                    return
                self._require_connection()
                self._client.set_type(args[0])
                print(f"Type set to {'ASCII' if args[0].upper() == 'A' else 'Binary'}.")
            case "MODE":
                if not self._require_exact_args(args, 1, "MODE {S | B | C}"):
                    return
                self._require_connection()
                self._client.set_mode(args[0])
                print(f"Mode set to {args[0].upper()}.")
            case "PORT":
                if not self._require_exact_args(args, 1, "PORT <h1,h2,h3,h4,p1,p2>"):
                    return
                self._require_connection()
                self._close_active_listener()
                self._active_listener = self._client._open_active_listener(args[0])
                print("Active mode configured.")
            case "PASV":
                if not self._require_exact_args(args, 0, "PASV"):
                    return
                self._require_connection()
                self._close_active_listener()
                print(self._client.pasv())
            case "STOR":
                if not self._require_exact_args(args, 1, "STOR <filename>"):
                    return
                self._require_connection()
                local = self._upload_file(args[0])
                print(f"Uploading {local} -> {args[0]} ...")
                if self._active_listener is not None:
                    digest = self._client.upload_active(local, args[0], listener=self._active_listener)
                    self._active_listener = None
                else:
                    digest = self._client.stor(local, args[0])
                print(f"Upload complete. SHA-256: {digest}")
            case "RETR":
                if not self._require_exact_args(args, 1, "RETR <filename>"):
                    return
                self._require_connection()
                local = self._download_file(args[0])
                print(f"Downloading {args[0]} -> {local} ...")
                if self._active_listener is not None:
                    digest = self._client.download_active(args[0], local, listener=self._active_listener)
                    self._active_listener = None
                else:
                    digest = self._client.download(args[0], local)
                print(f"Download complete. SHA-256: {digest}")
                print(f"Saved to: {local}")
            case "STOU":
                if not self._require_exact_args(args, 1, "STOU <local-file>"):
                    return
                self._require_connection()
                local = self._upload_file(args[0])
                digest = self._client.stou(local)
                print(f"Unique upload complete. SHA-256: {digest}")
            case "APPE":
                if not self._require_exact_args(args, 2, "APPE <local-file> <filename>"):
                    return
                self._require_connection()
                local = self._upload_file(args[0])
                digest = self._client.appe(local, args[1])
                print(f"Append complete. SHA-256: {digest}")
            case "DELE":
                if not self._require_exact_args(args, 1, "DELE <filename>"):
                    return
                self._require_connection()
                self._client.dele(args[0])
                print(f"Deleted '{args[0]}'.")
            case "RNFR":
                if not self._require_exact_args(args, 1, "RNFR <oldname>"):
                    return
                self._require_connection()
                self._client.rnfr(args[0])
                print("Rename source accepted; send RNTO <newname>.")
            case "RNTO":
                if not self._require_exact_args(args, 1, "RNTO <newname>"):
                    return
                self._require_connection()
                self._client.rnto(args[0])
                print("Rename successful.")
            case "HASH":
                if not self._require_exact_args(args, 1, "HASH <filename>"):
                    return
                self._require_connection()
                print(self._client.hash(args[0]))
            case "ABOR":
                if not self._require_exact_args(args, 0, "ABOR"):
                    return
                self._require_connection()
                print(self._client.abor())
            case "HELP":
                if not self._require_at_most_args(args, 1, "HELP [command]"):
                    return
                if self._client is None:
                    print(HELP_TEXT)
                elif args:
                    print(self._client.help(args[0]))
                else:
                    self._client.help()
                    print(HELP_TEXT)
            case _:
                print(f"Unknown command: {cmd!r}. Type 'HELP' for the approved FTP commands.")

    def _do_connect(self, args: list[str]) -> None:
        if not self._require_at_most_args(args, 2, "CONNECT [host [port]]"):
            return
        host = args[0] if args else "127.0.0.1"
        port = int(args[1]) if len(args) > 1 else 2121
        cfg = ClientConfig(host=host, control_port=port)
        self._client = FTPClient(cfg, trace_control=True)
        greeting = self._client.connect()
        print(f"Connected to {host}:{port} — {greeting}")

    @staticmethod
    def _require_exact_args(args: list[str], count: int, syntax: str) -> bool:
        if len(args) == count:
            return True
        print(f"Usage: {syntax}")
        return False

    @staticmethod
    def _require_at_most_args(args: list[str], count: int, syntax: str) -> bool:
        if len(args) <= count:
            return True
        print(f"Usage: {syntax}")
        return False

    def _upload_file(self, name: str) -> Path:
        path = Path(name)
        return path if path.is_absolute() else self._upload_root / path

    def _download_file(self, remote_name: str) -> Path:
        filename = Path(remote_name.replace("\\", "/")).name
        if not filename:
            raise FTPError(501, "RETR requires a filename")
        return self._download_root / filename

    def _require_connection(self) -> None:
        if self._client is None:
            raise FTPError(0, "Not connected. Use CONNECT first.")

    def _safe_quit(self) -> None:
        self._close_active_listener()
        if self._client is not None:
            try:
                self._client.quit()
            except Exception:
                self._client.close()
            self._client = None
            print("Disconnected.")

    def _close_active_listener(self) -> None:
        if self._active_listener is not None:
            try:
                self._active_listener.close()
            except OSError:
                pass
            self._active_listener = None

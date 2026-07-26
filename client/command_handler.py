"""Interactive CLI command handler for the Hybrid FTP client."""

from __future__ import annotations

import sys
from pathlib import Path

from common.config import ClientConfig
from .ftp_client import FTPClient, FTPError


HELP_TEXT = """\
Available commands:
  connect [host [port]]   Connect to server (default: 127.0.0.1:2121)
  login <user> <pass>     Authenticate
  logout / quit           Disconnect and exit
  pwd                     Print working directory
  cwd <path>              Change remote directory
  cdup                    Go to parent directory
  ls [path]               List directory (long format)
  nlst [path]             List filenames only
  mkd <name>              Create directory
  rmd <name>              Remove empty directory
  put <local> [remote]    Upload file via reliable UDP
  get <remote> [local]    Download file via reliable UDP
  put-active <local> [remote]  Upload through active-mode TCP setup
  get-active <remote> [local]  Download through active-mode TCP setup
  dele <name>             Delete remote file
  rename <old> <new>      Rename remote file
  size <name>             Show file size
  mdtm <name>             Show last modification time
  hash <name>             Show SHA-256 hash of remote file
  stat [path]             Show server/file status
  type <A|I>              Set transfer type (ASCII / Binary)
  noop                    Send keep-alive
  help                    Show this help
"""


class CLI:
    def __init__(self) -> None:
        self._client: FTPClient | None = None
        self._upload_root = Path("client/upload")
        self._download_root = Path("client/download")
        self._upload_root.mkdir(parents=True, exist_ok=True)
        self._download_root.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        print("Hybrid FTP Client. Type 'help' for commands.")
        while True:
            try:
                line = input("ftp> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self._safe_quit()
                break
            if not line:
                continue
            parts = line.split()
            cmd, args = parts[0].lower(), parts[1:]
            try:
                self._dispatch(cmd, args)
            except FTPError as exc:
                print(f"Error: {exc}")
            except Exception as exc:
                print(f"Unexpected error: {exc}")

    def _dispatch(self, cmd: str, args: list[str]) -> None:
        match cmd:
            case "connect":
                self._do_connect(args)
            case "login":
                self._require_connection()
                if len(args) < 2:
                    print("Usage: login <user> <pass>")
                    return
                self._client.login(args[0], args[1])
                print("Logged in.")
            case "logout" | "quit" | "exit" | "bye":
                self._safe_quit()
                sys.exit(0)
            case "pwd":
                self._require_connection()
                print(self._client.pwd())
            case "cwd" | "cd":
                self._require_connection()
                if not args:
                    print("Usage: cwd <path>")
                    return
                self._client.cwd(args[0])
                print(self._client.pwd())
            case "cdup":
                self._require_connection()
                self._client.cdup()
                print(self._client.pwd())
            case "ls" | "list" | "dir":
                self._require_connection()
                lines = self._client.list(args[0] if args else "")
                print("\n".join(lines) if lines else "(empty)")
            case "nlst":
                self._require_connection()
                lines = self._client.nlst(args[0] if args else "")
                print("\n".join(lines) if lines else "(empty)")
            case "mkd" | "mkdir":
                self._require_connection()
                if not args:
                    print("Usage: mkd <name>")
                    return
                self._client.mkd(args[0])
                print(f"Directory '{args[0]}' created.")
            case "rmd" | "rmdir":
                self._require_connection()
                if not args:
                    print("Usage: rmd <name>")
                    return
                self._client.rmd(args[0])
                print(f"Directory '{args[0]}' removed.")
            case "put" | "upload" | "put-active":
                self._require_connection()
                if not args:
                    print("Usage: put <local_file> [remote_name]")
                    return
                local = Path(args[0])
                if not local.is_absolute():
                    local = self._upload_root / local
                remote = args[1] if len(args) > 1 else local.name
                print(f"Uploading {local} -> {remote} ...")
                digest = self._client.upload_active(local, remote) if cmd == "put-active" else self._client.upload(local, remote)
                print(f"Upload complete. SHA-256: {digest}")
            case "get" | "download" | "get-active":
                self._require_connection()
                if not args:
                    print("Usage: get <remote_file> [local_name]")
                    return
                remote = args[0]
                local_name = args[1] if len(args) > 1 else remote
                local = self._download_root / local_name
                print(f"Downloading {remote} -> {local} ...")
                digest = self._client.download_active(remote, local) if cmd == "get-active" else self._client.download(remote, local)
                print(f"Download complete. SHA-256: {digest}")
                print(f"Saved to: {local}")
            case "dele" | "delete" | "rm":
                self._require_connection()
                if not args:
                    print("Usage: dele <name>")
                    return
                self._client.dele(args[0])
                print(f"Deleted '{args[0]}'.")
            case "rename" | "mv":
                self._require_connection()
                if len(args) < 2:
                    print("Usage: rename <old> <new>")
                    return
                self._client.rename(args[0], args[1])
                print(f"Renamed '{args[0]}' -> '{args[1]}'.")
            case "size":
                self._require_connection()
                if not args:
                    print("Usage: size <name>")
                    return
                print(f"{self._client.size(args[0])} bytes")
            case "mdtm":
                self._require_connection()
                if not args:
                    print("Usage: mdtm <name>")
                    return
                print(self._client.mdtm(args[0]))
            case "hash":
                self._require_connection()
                if not args:
                    print("Usage: hash <name>")
                    return
                print(self._client.hash(args[0]))
            case "stat":
                self._require_connection()
                print(self._client.stat(args[0] if args else ""))
            case "type":
                self._require_connection()
                if not args:
                    print("Usage: type <A|I>")
                    return
                self._client.set_type(args[0])
                print(f"Type set to {'ASCII' if args[0].upper() == 'A' else 'Binary'}.")
            case "noop":
                self._require_connection()
                self._client.noop()
                print("OK")
            case "help" | "?":
                print(HELP_TEXT)
            case _:
                print(f"Unknown command: {cmd!r}. Type 'help' for a list.")

    def _do_connect(self, args: list[str]) -> None:
        host = args[0] if args else "127.0.0.1"
        port = int(args[1]) if len(args) > 1 else 2121
        cfg = ClientConfig(host=host, control_port=port)
        # Show the live TCP control exchange in every interactive CLI session.
        self._client = FTPClient(cfg, trace_control=True)
        greeting = self._client.connect()
        print(f"Connected to {host}:{port} — {greeting}")

    def _require_connection(self) -> None:
        if self._client is None:
            raise FTPError(0, "Not connected. Use 'connect' first.")

    def _safe_quit(self) -> None:
        if self._client is not None:
            try:
                self._client.quit()
            except Exception:
                self._client.close()
            self._client = None
            print("Disconnected.")

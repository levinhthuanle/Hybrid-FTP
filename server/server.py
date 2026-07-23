"""TCP accept loop and thread management for the FTP server."""

from __future__ import annotations

import socket
import threading
from datetime import datetime

from common.config import ServerConfig

from .session import ClientSession


class FTPServer:
    def __init__(self, config: ServerConfig | None = None) -> None:
        self._config = config or ServerConfig()
        self._server_sock: socket.socket | None = None
        self._running = False
        self._threads: list[threading.Thread] = []
        self._print_lock = threading.Lock()

    def start(self) -> None:
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self._config.host, self._config.control_port))
        self._server_sock.listen(self._config.control_backlog)
        self._running = True
        self._log(f"[SERVER] Listening on {self._config.host}:{self._config.control_port}")
        self._accept_loop()

    def stop(self) -> None:
        self._running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
        for t in self._threads:
            t.join(timeout=2)
        self._log("[SERVER] Stopped")

    def _accept_loop(self) -> None:
        while self._running:
            try:
                conn, addr = self._server_sock.accept()
            except OSError:
                break
            self._log(f"[{addr[0]}:{addr[1]}] Connected")
            t = threading.Thread(
                target=self._handle_client,
                args=(conn, addr),
                daemon=True,
                name=f"client-{addr[0]}:{addr[1]}",
            )
            t.start()
            self._threads.append(t)

    def _handle_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        try:
            session = ClientSession(conn, addr, self._config, self._log)
            session.run()
        except Exception as exc:
            self._log(f"[{addr[0]}:{addr[1]}] Unhandled error: {exc}")
        finally:
            try:
                conn.close()
            except OSError:
                pass
            self._log(f"[{addr[0]}:{addr[1]}] Disconnected")

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._print_lock:
            print(f"[{ts}] {message}", flush=True)

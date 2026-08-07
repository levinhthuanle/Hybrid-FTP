"""Centralized configuration defaults for local development and testing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import DEFAULT_UDP_WINDOW_SIZE


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str = "127.0.0.1"
    advertise_host: str | None = None
    control_port: int = 2121
    udp_port: int = 2122
    storage_root: Path = Path("server/storage")
    control_backlog: int = 16
    udp_timeout_seconds: float = 0.5
    udp_max_retries: int = 10
    udp_window_size: int = DEFAULT_UDP_WINDOW_SIZE


@dataclass(frozen=True, slots=True)
class ClientConfig:
    host: str = "127.0.0.1"
    control_port: int = 2121
    download_root: Path = Path("client/download")
    upload_root: Path = Path("client/upload")
    udp_window_size: int = DEFAULT_UDP_WINDOW_SIZE

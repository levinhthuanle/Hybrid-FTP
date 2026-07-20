"""Integrity helpers used by the UDP data plane and completed files."""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path


def crc32(data: bytes) -> int:
    """Return an unsigned CRC-32 suitable for a packet checksum field."""

    return zlib.crc32(data) & 0xFFFFFFFF


def sha256_file(path: str | Path, chunk_size: int = 64 * 1024) -> str:
    """Return the hexadecimal SHA-256 digest of *path* without loading it all."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


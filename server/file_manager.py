"""Sandboxed filesystem operations for the FTP server."""

from __future__ import annotations

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import IO

from common.checksum import sha256_file


class PathError(PermissionError):
    """Raised when a resolved path escapes the storage root."""


class FileManager:
    def __init__(self, storage_root: Path) -> None:
        self._root = Path(storage_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def resolve(self, virtual_path: str, cwd: Path) -> Path:
        """Resolve *virtual_path* relative to *cwd* and assert it stays inside root."""
        if virtual_path.startswith("/"):
            candidate = self._root / virtual_path.lstrip("/")
        else:
            candidate = self._root / str(cwd).lstrip("/") / virtual_path
        resolved = candidate.resolve()
        if not str(resolved).startswith(str(self._root)):
            raise PathError(f"path escapes storage root: {virtual_path!r}")
        return resolved

    def to_virtual(self, real_path: Path) -> str:
        """Convert an absolute real path back to a virtual path string."""
        try:
            rel = real_path.relative_to(self._root)
        except ValueError:
            return "/"
        return "/" + str(rel)

    # ------------------------------------------------------------------
    # Directory operations
    # ------------------------------------------------------------------

    def list_dir(self, path: Path) -> list[str]:
        """Return LIST-style lines (like `ls -l`) for each entry in *path*."""
        lines: list[str] = []
        for entry in sorted(path.iterdir()):
            st = entry.stat()
            mode = stat.filemode(st.st_mode)
            nlinks = st.st_nlink
            size = st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime).strftime("%b %d %H:%M")
            lines.append(f"{mode} {nlinks:3d} owner group {size:12d} {mtime} {entry.name}")
        return lines

    def nlst_dir(self, path: Path) -> list[str]:
        """Return bare filenames for NLST."""
        return sorted(e.name for e in path.iterdir())

    def make_dir(self, path: Path) -> None:
        path.mkdir(parents=False, exist_ok=False)

    def remove_dir(self, path: Path) -> None:
        path.rmdir()

    def change_dir(self, current: Path, arg: str) -> Path:
        new = self.resolve(arg, current)
        if not new.is_dir():
            raise NotADirectoryError(f"not a directory: {arg!r}")
        return new

    # ------------------------------------------------------------------
    # File metadata
    # ------------------------------------------------------------------

    def file_size(self, path: Path) -> int:
        return path.stat().st_size

    def file_mdtm(self, path: Path) -> str:
        mtime = datetime.fromtimestamp(path.stat().st_mtime)
        return mtime.strftime("%Y%m%d%H%M%S")

    def file_hash(self, path: Path) -> str:
        return sha256_file(path)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def delete_file(self, path: Path) -> None:
        path.unlink()

    def rename(self, src: Path, dst: Path) -> None:
        src.rename(dst)

    # ------------------------------------------------------------------
    # Transfer hooks (filled in by RDT layer later)
    # ------------------------------------------------------------------

    def open_for_read(self, path: Path) -> IO[bytes]:
        return path.open("rb")

    def open_for_write(self, path: Path, mode: str = "wb") -> IO[bytes]:
        return path.open(mode)

    def unique_path(self, directory: Path, basename: str = "file") -> Path:
        candidate = directory / basename
        counter = 1
        while candidate.exists():
            stem, _, suffix = basename.rpartition(".")
            if suffix:
                candidate = directory / f"{stem}.{counter}.{suffix}"
            else:
                candidate = directory / f"{basename}.{counter}"
            counter += 1
        return candidate

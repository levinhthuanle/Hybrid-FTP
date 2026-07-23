"""Credential store for the FTP server."""

from __future__ import annotations

USERS: dict[str, str] = {
    "admin": "1234",
    "anonymous": "",
}


def username_exists(username: str) -> bool:
    return username in USERS


def verify(username: str, password: str) -> bool:
    expected = USERS.get(username)
    return expected is not None and expected == password

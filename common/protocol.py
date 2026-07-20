"""Line-oriented TCP control-channel protocol helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .constants import CONTROL_LINE_ENDING, ENCODING, MAX_CONTROL_LINE


class ReplyCode(IntEnum):
    SERVICE_READY = 220
    GOODBYE = 221
    COMMAND_OK = 200
    LOGIN_SUCCESSFUL = 230
    FILE_ACTION_OK = 250
    DATA_CONNECTION_OPEN = 125
    OPENING_DATA_CONNECTION = 150
    TRANSFER_COMPLETE = 226
    USERNAME_OK = 331
    RENAME_PENDING = 350
    SERVICE_UNAVAILABLE = 421
    CANNOT_OPEN_DATA_CONNECTION = 425
    TRANSFER_ABORTED = 426
    FILE_UNAVAILABLE_TRANSIENT = 450
    SYNTAX_ERROR = 500
    PARAMETER_ERROR = 501
    COMMAND_NOT_IMPLEMENTED = 502
    NOT_LOGGED_IN = 530
    FILE_UNAVAILABLE = 550


@dataclass(frozen=True, slots=True)
class Command:
    name: str
    argument: str | None = None


def parse_command(line: str) -> Command:
    """Parse one CRLF-stripped control line into an uppercase command."""

    line = line.strip("\r\n")
    if not line or len(line) > MAX_CONTROL_LINE:
        raise ValueError("control command is empty or too long")
    name, separator, argument = line.partition(" ")
    if not name.isascii() or not name.isalpha():
        raise ValueError("command name must contain ASCII letters only")
    return Command(name.upper(), argument.strip() if separator and argument.strip() else None)


def format_reply(code: ReplyCode | int, message: str) -> bytes:
    """Format a standards-style single-line FTP response for TCP transmission."""

    return f"{int(code)} {message}{CONTROL_LINE_ENDING}".encode(ENCODING)


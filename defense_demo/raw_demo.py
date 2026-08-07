#!/usr/bin/env python3
"""Helpers for FTP commands that are awkward to demo from the main CLI."""

from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from client.ftp_client import FTPClient, FTPError
from common.config import ClientConfig
from transport.udp_sender import UDPSender


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hybrid FTP defense helper")
    parser.add_argument("--host", default="127.0.0.1", help="FTP server host")
    parser.add_argument("--port", type=int, default=2121, help="FTP control port")
    parser.add_argument("--user", default="admin", help="Username")
    parser.add_argument("--password", default="1234", help="Password")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("help", help="Show raw FTP HELP reply")

    mode = subparsers.add_parser("mode", help="Send MODE directly")
    mode.add_argument("mode", help="Mode code, usually S or B")

    stat = subparsers.add_parser("stat", help="Show STAT reply")
    stat.add_argument("path", nargs="?", default="", help="Optional remote path")
    stat.add_argument("--cwd", default="", help="Remote cwd before running STAT")

    stou = subparsers.add_parser("stou", help="Upload with STOU")
    stou.add_argument("local", help="Local file path")
    stou.add_argument("--cwd", default="", help="Remote cwd before transfer")

    appe = subparsers.add_parser("appe", help="Append to a remote file")
    appe.add_argument("local", help="Local file path")
    appe.add_argument("remote", help="Remote file name")
    appe.add_argument("--cwd", default="", help="Remote cwd before transfer")

    abor = subparsers.add_parser("abor", help="Start STOR then abort it")
    abor.add_argument("remote", help="Remote file name")
    abor.add_argument("--cwd", default="", help="Remote cwd before transfer")

    return parser


def open_client(args: argparse.Namespace) -> FTPClient:
    client = FTPClient(
        ClientConfig(host=args.host, control_port=args.port),
        trace_control=True,
    )
    client.connect()
    client.login(args.user, args.password)
    return client


def maybe_cwd(client: FTPClient, cwd: str) -> None:
    if cwd:
        client.cwd(cwd)


def run_help(args: argparse.Namespace) -> int:
    client = open_client(args)
    try:
        print(client.help())
        return 0
    finally:
        safe_quit(client)


def run_mode(args: argparse.Namespace) -> int:
    client = open_client(args)
    try:
        code, message = client._cmd(f"MODE {args.mode}")
        print(f"MODE {args.mode} -> {code} {message}")
        return 0 if code < 400 else 1
    finally:
        safe_quit(client)


def run_stat(args: argparse.Namespace) -> int:
    client = open_client(args)
    try:
        maybe_cwd(client, args.cwd)
        print(client.stat(args.path))
        return 0
    finally:
        safe_quit(client)


def run_stou(args: argparse.Namespace) -> int:
    client = open_client(args)
    local_path = Path(args.local)
    if not local_path.is_file():
        raise SystemExit(f"Local file not found: {local_path}")

    try:
        maybe_cwd(client, args.cwd)
        before = set(client.nlst())
        data_sock = client._open_pasv_data()
        udp_sock: socket.socket | None = None
        try:
            code, message = client._cmd("STOU")
            if code != 150:
                raise FTPError(code, message)
            udp_port, tid = client._parse_udp_params(message)
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.connect((args.host, udp_port))
            digest = UDPSender(udp_sock, tid).send_file(local_path)
        finally:
            if udp_sock is not None:
                udp_sock.close()
            data_sock.close()

        code, message = client._read_reply()
        if code != 226:
            raise FTPError(code, message)

        after = set(client.nlst())
        created = sorted(after - before)
        print(f"STOU digest: {digest}")
        if created:
            print(f"Created remote file: {created[0]}")
        else:
            print("Created remote file: could not infer exact name from NLST diff")
        return 0
    finally:
        safe_quit(client)


def run_appe(args: argparse.Namespace) -> int:
    client = open_client(args)
    local_path = Path(args.local)
    if not local_path.is_file():
        raise SystemExit(f"Local file not found: {local_path}")

    try:
        maybe_cwd(client, args.cwd)
        data_sock = client._open_pasv_data()
        udp_sock: socket.socket | None = None
        try:
            code, message = client._cmd(f"APPE {args.remote}")
            if code != 150:
                raise FTPError(code, message)
            udp_port, tid = client._parse_udp_params(message)
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.connect((args.host, udp_port))
            digest = UDPSender(udp_sock, tid).send_file(local_path)
        finally:
            if udp_sock is not None:
                udp_sock.close()
            data_sock.close()

        code, message = client._read_reply()
        if code != 226:
            raise FTPError(code, message)

        final_hash = client.hash(args.remote)
        print(f"APPE chunk digest: {digest}")
        print(f"Remote file SHA-256 after append: {final_hash}")
        return 0
    finally:
        safe_quit(client)


def run_abor(args: argparse.Namespace) -> int:
    client = open_client(args)
    try:
        maybe_cwd(client, args.cwd)
        data_sock = client._open_pasv_data()
        try:
            code, message = client._cmd(f"STOR {args.remote}")
            if code != 150:
                raise FTPError(code, message)
            code, message = client._cmd("ABOR")
            print(f"ABOR -> {code} {message}")
        finally:
            data_sock.close()

        time.sleep(0.1)
        try:
            client.hash(args.remote)
            print("Abort verification: remote file still exists")
            return 1
        except FTPError as exc:
            if exc.code == 550:
                print("Abort verification: remote file was not created")
                return 0
            raise
    finally:
        safe_quit(client)


def safe_quit(client: FTPClient) -> None:
    try:
        client.quit()
    except Exception:
        client.close()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    match args.command:
        case "help":
            return run_help(args)
        case "mode":
            return run_mode(args)
        case "stat":
            return run_stat(args)
        case "stou":
            return run_stou(args)
        case "appe":
            return run_appe(args)
        case "abor":
            return run_abor(args)
        case _:
            parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())

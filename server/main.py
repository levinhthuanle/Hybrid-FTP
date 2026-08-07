"""Entry point: python -m server.main"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import ServerConfig
from server import FTPServer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Hybrid FTP server")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Control/data bind address. Use 0.0.0.0 to listen on the LAN.",
    )
    parser.add_argument(
        "--advertise-host",
        default=None,
        help="IPv4 address advertised in PASV replies. Defaults to the local address of each client connection.",
    )
    parser.add_argument("--port", type=int, default=2121, help="FTP control port")
    return parser.parse_args()

if __name__ == "__main__":
    args = _parse_args()
    server = FTPServer(
        ServerConfig(
            host=args.host,
            advertise_host=args.advertise_host,
            control_port=args.port,
        )
    )
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

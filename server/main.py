"""Entry point: python -m server.main"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import ServerConfig
from server import FTPServer

if __name__ == "__main__":
    server = FTPServer(ServerConfig())
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

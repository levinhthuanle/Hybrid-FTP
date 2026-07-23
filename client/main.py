"""Entry point: python -m client.main  or  python3 client/main.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from client.command_handler import CLI

if __name__ == "__main__":
    CLI().run()

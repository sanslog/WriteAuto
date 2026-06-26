"""Entry point redirect — prefer `python main.py` from project root instead."""

import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import main

if __name__ == "__main__":
    main(dev="--dev" in sys.argv)

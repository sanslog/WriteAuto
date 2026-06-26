"""Run with: python -m backend [--dev]"""
import sys
sys.path.insert(0, ".")
from main import main
main("--dev" in sys.argv)

#!/usr/bin/env python
"""Entry point to run Django management commands from the repo root."""
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / 'mysite'
if PROJECT_DIR.exists():
    sys.path.insert(0, str(PROJECT_DIR))

from mysite.manage import main


if __name__ == '__main__':
    main()

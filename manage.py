#!/usr/bin/env python
"""Thin wrapper so Railway (and local) can call manage.py from repo root."""
from pathlib import Path
import runpy
import sys

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / 'mysite'
INNER_MANAGE = PROJECT_DIR / 'manage.py'


def main():
    if not INNER_MANAGE.exists():
        raise SystemExit('No se encontró mysite/manage.py; revisa la estructura del proyecto.')
    sys.path.insert(0, str(PROJECT_DIR))
    runpy.run_path(str(INNER_MANAGE), run_name='__main__')


if __name__ == '__main__':
    main()

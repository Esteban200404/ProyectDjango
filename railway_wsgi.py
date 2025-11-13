"""
WSGI entrypoint for Railway / Procfile deployments.

This file lives at the repo root so Gunicorn can import it without needing
extra PYTHONPATH tweaks. It simply ensures the inner Django project directory
(`mysite/`) is on sys.path and then hands off to the real `mysite.wsgi`.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / 'mysite'

# Ensure the inner project dir is importable as the `mysite` package.
project_path = str(PROJECT_DIR)
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from mysite.wsgi import application  # noqa: E402  (import after sys.path tweak)

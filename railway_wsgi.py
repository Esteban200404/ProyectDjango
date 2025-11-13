"""
WSGI entrypoint for Railway / Procfile deployments.

This file lives at the repo root so Gunicorn can import it without needing
extra PYTHONPATH tweaks. It ensures the inner Django project directory
(`mysite/`) is on sys.path and then loads the actual Django WSGI application.
"""

from importlib import util as importlib_util
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = ROOT_DIR / 'mysite'
INNER_WSGI = PROJECT_DIR / 'mysite' / 'wsgi.py'

# Ensure the inner project dir is importable as the `mysite` package.
project_path = str(PROJECT_DIR)
if project_path not in sys.path:
    sys.path.insert(0, project_path)

try:
    from mysite.wsgi import application  # type: ignore  # noqa: E402
except ModuleNotFoundError:
    # On some deploy targets the nested package isn't importable even after the
    # sys.path tweak above. Fall back to loading wsgi.py directly by path.
    if not INNER_WSGI.is_file():
        raise

    spec = importlib_util.spec_from_file_location('mysite_wsgi', INNER_WSGI)
    if spec is None or spec.loader is None:
        raise RuntimeError('Unable to load mysite.wsgi via fallback loader.')

    module = importlib_util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    application = module.application  # type: ignore[attr-defined]

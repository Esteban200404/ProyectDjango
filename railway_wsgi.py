# railway_wsgi.py
from pathlib import Path
import os
import sys

from django.core.wsgi import get_wsgi_application

ROOT_DIR = Path(__file__).resolve().parent  # carpeta donde está este archivo
MYSITE_DIR = ROOT_DIR / 'mysite'

# Asegurar que el root del repo (/app) y mysite están en sys.path
root_path = str(ROOT_DIR)
mysite_path = str(MYSITE_DIR)

if root_path not in sys.path:
    sys.path.insert(0, root_path)

if mysite_path not in sys.path:
    sys.path.insert(0, mysite_path)

# Nombre del proyecto Django (la carpeta donde están settings.py, urls.py, etc.)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = get_wsgi_application()

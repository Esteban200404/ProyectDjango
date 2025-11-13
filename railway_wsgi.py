# railway_wsgi.py
from pathlib import Path
import os
import sys

from django.core.wsgi import get_wsgi_application

ROOT_DIR = Path(__file__).resolve().parent  # carpeta donde está este archivo

# Asegurar que el root del repo (/app) está en sys.path
root_path = str(ROOT_DIR)
if root_path not in sys.path:
    sys.path.insert(0, root_path)

# Nombre del proyecto Django (la carpeta donde están settings.py, urls.py, etc.)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

application = get_wsgi_application()

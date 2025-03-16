"""
WSGI config for darf_vermieter_das project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "darf_vermieter_das.settings")

# Get the default WSGI application
application = get_wsgi_application()

# Get the base directory (two levels up from the current file)
BASE_DIR = Path(__file__).resolve().parent.parent
staticfiles_dir = BASE_DIR / "staticfiles"

# Use the BASE_DIR path for WhiteNoise
application = WhiteNoise(application, root=staticfiles_dir)

# Make the app variable available to the Vercel serverless function
app = application

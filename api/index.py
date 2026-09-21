"""
Vercel serverless entrypoint.

Vercel imports ``app`` from this module and calls it for every request that
vercel.json routes here.

Nothing from the project may be imported above get_wsgi_application(). Importing
a model, a view or the URLconf first touches the app registry before
django.setup() has run, which raises AppRegistryNotReady ("Apps aren't loaded
yet") at import time and fails the whole function rather than one request.
"""

import os
import sys
from pathlib import Path

# Vercel does not put the repository root on sys.path, so `config` and `apps`
# are not importable without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application  # noqa: E402  (see docstring)

app = get_wsgi_application()

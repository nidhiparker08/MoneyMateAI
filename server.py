"""ASGI entrypoint used by supervisor's uvicorn command.

Supervisor runs: `uvicorn server:app --host 0.0.0.0 --port 8001` from /app/backend.
We expose Django's ASGI application as `app` so the existing supervisor config keeps
working without any modifications.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "FinSyncAI.settings")

from django.core.asgi import get_asgi_application  # noqa: E402

app = get_asgi_application()

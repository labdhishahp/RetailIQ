"""Vercel serverless entrypoint for the RetailIQ FastAPI backend.

Vercel's Python runtime looks for an ASGI app named `app` in files under /api.
The application itself lives in backend/app, so that directory is put on the
import path here rather than duplicating any code.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402

__all__ = ["app"]

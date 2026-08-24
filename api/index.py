"""Vercel serverless entry point.

Vercel's Python runtime looks for a module-level ASGI application called
``app``. Everything else lives in the ``app`` package, so this file is a
re-export and nothing more.

Deploying elsewhere (Render, Railway, Fly, Cloud Run) does not use this file;
those platforms run ``uvicorn app.main:app`` directly.
"""

from app.main import app

__all__ = ["app"]

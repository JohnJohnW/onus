"""Vercel serverless entrypoint for the Onus engine (demo hosting only).

Exposes the FastAPI ASGI app to Vercel's Python runtime. Real / Australian deployments
use the Docker image and a long-running server instead (see docs/deployment/README.md).

Demo trade-offs on Vercel's free serverless runtime (also surfaced on the app's /hosting
page): the filesystem is ephemeral so uploaded documents do not persist, long AI calls
can hit the function timeout, and migrations are run separately (a GitHub Action), not on
start.
"""
import os
import sys

# Make the engine package (main, routers, database, ...) importable from this subdir.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402

# Vercel's Python runtime serves this module-level ASGI application.
__all__ = ["app"]

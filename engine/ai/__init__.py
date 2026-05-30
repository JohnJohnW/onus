"""Provider-agnostic AI layer for the Onus engine.

All AI calls should go through :func:`get_ai_provider`, which returns the
provider configured via the ``AI_PROVIDER`` environment variable.
"""
from __future__ import annotations

from ai.base import AIProvider
from ai.factory import get_ai_provider

__all__ = ["AIProvider", "get_ai_provider"]

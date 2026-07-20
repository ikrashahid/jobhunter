"""Shared FastAPI dependencies."""

from __future__ import annotations

import hmac
import os
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Header, HTTPException

# Ensure API_KEY / CORS_* are available even before any DB call.
for _parent in Path(__file__).resolve().parents:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=False)
        break


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    Reject any request that doesn't present the shared secret.

    Compare with hmac.compare_digest so timing doesn't leak how much of
    the key was guessed correctly. Fail closed if API_KEY isn't set —
    an open backend is worse than a temporarily broken one.
    """
    expected = os.getenv("API_KEY", "")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="API_KEY is not configured on the server",
        )
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Trigger rate limiting (in-process; fine for a single Railway worker) ──

_TRIGGER_COOLDOWN_SEC = int(os.getenv("TRIGGER_COOLDOWN_SEC", "120"))
_last_trigger_at: dict[str, float] = defaultdict(float)
_trigger_in_flight = False


def enforce_trigger_rate_limit(action: str) -> None:
    """
    Gate expensive pipeline spawns.

    - One cooldown window per action (fetch / score / draft)
    - Global in-flight lock so overlapping triggers can't stack
    """
    global _trigger_in_flight

    if _trigger_in_flight:
        raise HTTPException(
            status_code=429,
            detail="A pipeline trigger is already running — try again shortly",
        )

    now = time.monotonic()
    elapsed = now - _last_trigger_at[action]
    if elapsed < _TRIGGER_COOLDOWN_SEC:
        wait = int(_TRIGGER_COOLDOWN_SEC - elapsed) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Trigger '{action}' is rate-limited — retry in {wait}s",
        )

    _last_trigger_at[action] = now


def mark_trigger_started() -> None:
    global _trigger_in_flight
    _trigger_in_flight = True


def mark_trigger_finished() -> None:
    global _trigger_in_flight
    _trigger_in_flight = False

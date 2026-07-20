import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

from api.deps import (
    enforce_trigger_rate_limit,
    mark_trigger_finished,
    mark_trigger_started,
)
from api.models import TriggerDraftRequest

router = APIRouter()

PIPELINE_DIR = str(Path(__file__).parent.parent.parent.parent / "pipeline")


def _run_script(script_name: str) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, f"{PIPELINE_DIR}/{script_name}"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-500:] if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "script exceeded 5 minute limit"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _gated(action: str, script_name: str) -> dict:
    enforce_trigger_rate_limit(action)
    mark_trigger_started()
    try:
        return _run_script(script_name)
    finally:
        mark_trigger_finished()


@router.post("/trigger/fetch")
async def trigger_fetch():
    return _gated("fetch", "run.py")


@router.post("/trigger/score")
async def trigger_score():
    return _gated("score", "run_phase3.py")


@router.post("/trigger/draft")
async def trigger_draft(body: TriggerDraftRequest | None = None):
    return _gated("draft", "run_phase4.py")

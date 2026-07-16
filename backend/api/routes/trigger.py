import subprocess
import sys
from fastapi import APIRouter
from api.models import TriggerDraftRequest

router = APIRouter()

PIPELINE_DIR = str(__import__("pathlib").Path(__file__).parent.parent.parent.parent / "pipeline")


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
            "stdout": result.stdout[-2000:],  # last 2000 chars
            "stderr": result.stderr[-500:] if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "script exceeded 5 minute limit"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/trigger/fetch")
async def trigger_fetch():
    return _run_script("run.py")


@router.post("/trigger/score")
async def trigger_score():
    return _run_script("run_phase3.py")


@router.post("/trigger/draft")
async def trigger_draft(body: TriggerDraftRequest | None = None):
    return _run_script("run_phase4.py")
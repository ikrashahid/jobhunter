from fastapi import APIRouter
from api.services.db import get_client

router = APIRouter()


@router.get("/stats")
async def get_stats():
    client = get_client()

    postings = client.table("postings").select("id", count="exact").execute()
    embedded = client.table("postings").select("id", count="exact").not_.is_("embedding", "null").execute()
    matches = client.table("matches").select("id, score, draft_status, draft", count="exact").execute()

    total_matches = matches.count or 0
    drafted = len([m for m in (matches.data or []) if m.get("draft")])
    failed_token = len([m for m in (matches.data or []) if m.get("draft_status") == "failed_token_limit"])
    pending = len([m for m in (matches.data or []) if not m.get("draft") and m.get("draft_status") != "failed_token_limit"])

    scores = [m["score"] for m in (matches.data or []) if m.get("score")]
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0

    source_resp = client.table("postings").select("source").execute()
    source_breakdown = {}
    for row in (source_resp.data or []):
        s = row["source"]
        source_breakdown[s] = source_breakdown.get(s, 0) + 1

    # schema.sql uses started_at (not run_at). Don't let a missing/empty
    # pipeline_runs table take down the whole dashboard.
    last_run = None
    try:
        pipeline_runs = (
            client.table("pipeline_runs")
            .select("started_at, finished_at, status")
            .order("started_at", desc=True)
            .limit(1)
            .execute()
        )
        if pipeline_runs.data:
            last_run = pipeline_runs.data[0].get("started_at")
    except Exception:
        last_run = None

    return {
        "postings": {
            "total": postings.count or 0,
            "embedded": embedded.count or 0,
            "embedding_coverage": round((embedded.count or 0) / max(postings.count or 1, 1), 3),
        },
        "matches": {
            "total": total_matches,
            "drafted": drafted,
            "failed_token_limit": failed_token,
            "pending": pending,
            "draft_success_rate": round(drafted / max(total_matches, 1), 3),
        },
        "scores": {
            "average": avg_score,
            "distribution": _build_distribution(scores),
        },
        "sources": source_breakdown,
        "last_run": last_run,
    }


def _build_distribution(scores: list[float]) -> dict:
    """Buckets scores into ranges for histogram display."""
    buckets = {"0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0, "0.6-0.8": 0, "0.8-1.0": 0}
    for s in scores:
        if s < 0.2: buckets["0.0-0.2"] += 1
        elif s < 0.4: buckets["0.2-0.4"] += 1
        elif s < 0.6: buckets["0.4-0.6"] += 1
        elif s < 0.8: buckets["0.6-0.8"] += 1
        else: buckets["0.8-1.0"] += 1
    return buckets
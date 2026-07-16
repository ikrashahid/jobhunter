from fastapi import APIRouter
from api.services.db import get_client
import json

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    client = get_client()

    matches = client.table("matches").select(
        "id, score, human_label, tailored_resume, draft_status"
    ).execute()

    rows = matches.data or []

    # Precision@k from human labels
    labeled = [r for r in rows if r.get("human_label") in ("good_fit", "bad_fit")]
    good_labels = [r for r in labeled if r.get("human_label") == "good_fit"]

    sorted_by_score = sorted(rows, key=lambda x: x.get("score") or 0, reverse=True)
    top5 = sorted_by_score[:5]
    top10 = sorted_by_score[:10]

    def precision_at_k(top_k: list) -> float | None:
        labeled_in_k = [r for r in top_k if r.get("human_label") in ("good_fit", "bad_fit")]
        if not labeled_in_k:
            return None
        good_in_k = [r for r in labeled_in_k if r.get("human_label") == "good_fit"]
        return round(len(good_in_k) / len(labeled_in_k), 3)

    # Faithfulness and quality from tailored_resume JSON
    faithfulness_scores = []
    quality_scores = []

    for row in rows:
        meta = row.get("tailored_resume")
        if meta:
            try:
                data = json.loads(meta) if isinstance(meta, str) else meta
                f = data.get("faithfulness_score")
                q = data.get("quality_score")
                if f is not None:
                    faithfulness_scores.append(float(f))
                if q is not None:
                    quality_scores.append(float(q))
            except Exception:
                pass

    def safe_avg(lst): return round(sum(lst) / len(lst), 3) if lst else None
    def safe_min(lst): return round(min(lst), 3) if lst else None
    def safe_max(lst): return round(max(lst), 3) if lst else None

    draft_success = len([r for r in rows if r.get("draft_status") == "drafted" or (r.get("tailored_resume") and not r.get("draft_status"))])
    token_failures = len([r for r in rows if r.get("draft_status") == "failed_token_limit"])

    return {
        "precision": {
            "at_5": precision_at_k(top5),
            "at_10": precision_at_k(top10),
            "labeled_count": len(labeled),
            "good_fit_count": len(good_labels),
        },
        "faithfulness": {
            "mean": safe_avg(faithfulness_scores),
            "min": safe_min(faithfulness_scores),
            "max": safe_max(faithfulness_scores),
            "sample_count": len(faithfulness_scores),
        },
        "quality": {
            "mean": safe_avg(quality_scores),
            "min": safe_min(quality_scores),
            "max": safe_max(quality_scores),
            "sample_count": len(quality_scores),
        },
        "pipeline": {
            "draft_success_count": draft_success,
            "token_failure_count": token_failures,
            "total_matches": len(rows),
        },
    }
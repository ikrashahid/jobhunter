from fastapi import APIRouter, Query
from api.services.db import get_client
from api.models import MatchStatusUpdate

router = APIRouter()


@router.get("/matches")
async def get_matches(
    status: str | None = Query(None),
    source: str | None = Query(None),
    min_score: float = Query(0.0),
    page: int = Query(1),
    per_page: int = Query(10),
):
    client = get_client()

    query = (
        client.table("matches")
        .select("*, postings(title, company, description, url, source, pay_range, location, posted_at)")
        .gte("score", min_score)
        .order("score", desc=True)
        .range((page - 1) * per_page, page * per_page - 1)
    )

    # NOTE: the real column is `draft_status`, not `status` — matches
    # what pipeline.py/run_phase4.py write and what the frontend reads.
    # Using `status` here previously meant this filter (and the PATCH
    # endpoint below) silently targeted a column that doesn't exist.
    if status:
        query = query.eq("draft_status", status)

    # Filtering on a joined table's column needs the `table.column` form
    # in PostgREST — a plain `source` param was previously accepted but
    # never actually applied to the query at all.
    if source:
        query = query.eq("postings.source", source)

    result = query.execute()
    return {
        "matches": result.data or [],
        "page": page,
        "per_page": per_page,
    }


@router.get("/matches/{match_id}")
async def get_match(match_id: str):
    client = get_client()
    result = (
        client.table("matches")
        .select("*, postings(title, company, description, url, source, pay_range, location, posted_at)")
        .eq("id", match_id)
        .single()
        .execute()
    )
    return result.data


@router.patch("/matches/{match_id}")
async def update_match(match_id: str, body: MatchStatusUpdate):
    client = get_client()
    update_data = {}
    if body.status is not None:
        # Written to `draft_status` — see note above. This is the fix
        # that makes the frontend's unseen/reviewing/applied/rejected
        # buttons actually persist instead of only updating local state.
        update_data["draft_status"] = body.status
    if body.human_label is not None:
        update_data["human_label"] = body.human_label
    if body.application_status is not None:
        # 'red' | 'yellow' | 'green' — tracked separately from draft_status,
        # which is already overloaded (pipeline status + review status).
        update_data["application_status"] = body.application_status
    if body.applied_at is not None:
        update_data["applied_at"] = body.applied_at.isoformat()

    if not update_data:
        return {"error": "nothing to update"}

    result = client.table("matches").update(update_data).eq("id", match_id).execute()
    return result.data[0] if result.data else {"error": "not found"}
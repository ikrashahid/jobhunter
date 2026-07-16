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

    if status:
        query = query.eq("status", status)

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
        update_data["status"] = body.status
    if body.human_label is not None:
        update_data["human_label"] = body.human_label

    if not update_data:
        return {"error": "nothing to update"}

    result = client.table("matches").update(update_data).eq("id", match_id).execute()
    return result.data[0] if result.data else {"error": "not found"}
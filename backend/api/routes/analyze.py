import json
from fastapi import APIRouter
from api.models import JDAnalyzeRequest
from api.services.db import get_client
from api.services.jd_analyzer import analyze_jd

router = APIRouter()


@router.post("/analyze-jd")
async def analyze_job_description(body: JDAnalyzeRequest):
    client = get_client()

    result = analyze_jd(body.jd_text)

    stored = client.table("jd_analyses").insert({
        "jd_text": body.jd_text,
        "role_summary": result["role_summary"],
        "fit_analysis": result["fit_analysis"],
        "interview_questions": result["interview_questions"],
    }).execute()

    analysis_id = stored.data[0]["id"] if stored.data else None

    return {
        "id": analysis_id,
        **result,
    }


@router.get("/analyze-jd")
async def get_analyses():
    client = get_client()
    result = (
        client.table("jd_analyses")
        .select("id, created_at, role_summary, fit_analysis")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    return result.data or []
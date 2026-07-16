import os
import json
import tempfile
from fastapi import APIRouter
from fastapi.responses import FileResponse
from api.services.db import get_client
from api.services.pdf_gen import generate_cover_letter_pdf, generate_fit_pdf
from pathlib import Path

router = APIRouter()

CANDIDATE_NAME = "Iqra Shahid"
CANDIDATE_EMAIL = "iqras1607@gmail.com"


@router.get("/matches/{match_id}/pdf/cover-letter")
async def download_cover_letter(match_id: str):
    client = get_client()

    match = (
        client.table("matches")
        .select("draft, score, tailored_resume, postings(title, company)")
        .eq("id", match_id)
        .single()
        .execute()
    )

    if not match.data or not match.data.get("draft"):
        return {"error": "no draft found for this match"}

    data = match.data
    posting = data.get("postings") or {}

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = generate_cover_letter_pdf(
            candidate_name=CANDIDATE_NAME,
            candidate_email=CANDIDATE_EMAIL,
            job_title=posting.get("title", "Role"),
            company=posting.get("company", "Company"),
            cover_letter_text=data["draft"],
            output_path=tmp.name,
        )

    filename = f"cover_letter_{posting.get('company', 'company').replace(' ', '_')}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.get("/matches/{match_id}/pdf/fit")
async def download_fit_report(match_id: str):
    client = get_client()

    match = (
        client.table("matches")
        .select("draft, score, tailored_resume, postings(title, company)")
        .eq("id", match_id)
        .single()
        .execute()
    )

    if not match.data:
        return {"error": "match not found"}

    data = match.data
    posting = data.get("postings") or {}

    meta = {}
    try:
        raw = data.get("tailored_resume")
        meta = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        pass

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        path = generate_fit_pdf(
            candidate_name=CANDIDATE_NAME,
            job_title=posting.get("title", "Role"),
            company=posting.get("company", "Company"),
            match_score=data.get("score") or 0,
            faithfulness_score=meta.get("faithfulness_score"),
            quality_score=meta.get("quality_score"),
            fit_analysis=meta.get("fit_analysis", {}),
            cover_letter_text=data.get("draft") or "",
            verdicts=meta.get("verdicts", []),
            output_path=tmp.name,
        )

    filename = f"fit_report_{posting.get('company', 'company').replace(' ', '_')}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)
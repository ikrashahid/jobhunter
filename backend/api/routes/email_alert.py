import re

import httpx
from fastapi import APIRouter

from api.models import EmailAlertRequest

router = APIRouter()

# n8n forwards subjects shaped like:
#   "Chief Technology Officer (CTO) at Cyngro. 19 more ai developer jobs in Lahore"
# We only need the first "<title> at <company>" chunk before any trailing
# "N more jobs" filler Indeed appends.
_TITLE_AT_COMPANY = re.compile(
    r"^(?P<title>.+?)\s+at\s+(?P<company>[A-Za-z0-9&.\- ]+?)(?:[.,]|$)",
    re.IGNORECASE,
)


def parse_title_company(subject: str) -> tuple[str | None, str | None]:
    match = _TITLE_AT_COMPANY.search(subject)
    if not match:
        return None, None
    return match.group("title").strip(), match.group("company").strip()


def _slugify(company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", company.lower())


async def check_greenhouse(company: str, title: str) -> str | None:
    """Greenhouse job boards are keyed by a company slug, e.g. boards-api.greenhouse.io/v1/boards/anthropic/jobs"""
    slug = _slugify(company)
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return None
        jobs = resp.json().get("jobs", [])
        title_lower = title.lower()
        for job in jobs:
            if title_lower in job.get("title", "").lower():
                return job.get("absolute_url")
    except httpx.HTTPError:
        return None
    return None


async def check_lever(company: str, title: str) -> str | None:
    """Lever job boards: api.lever.co/v0/postings/<company-slug>"""
    slug = _slugify(company)
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return None
        jobs = resp.json()
        title_lower = title.lower()
        for job in jobs:
            if title_lower in job.get("text", "").lower():
                return job.get("hostedUrl")
    except httpx.HTTPError:
        return None
    return None


@router.post("/process-email-alert")
async def process_email_alert(body: EmailAlertRequest):
    title, company = parse_title_company(body.subject)

    if not title or not company:
        return {
            "found": False,
            "reason": "could_not_parse_subject",
            "subject": body.subject,
        }

    url = await check_greenhouse(company, title)
    source = "greenhouse"
    if not url:
        url = await check_lever(company, title)
        source = "lever"

    if url:
        return {
            "found": True,
            "title": title,
            "company": company,
            "source": source,
            "url": url,
        }

    return {
        "found": False,
        "reason": "no_direct_listing",
        "title": title,
        "company": company,
    }
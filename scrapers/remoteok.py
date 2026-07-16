import os
import requests
from dateutil import parser as dateparser

# RemoteOK's public JSON API — no API key needed, but it blocks requests
# that don't send a real-looking User-Agent header, so we set one below.
REMOTEOK_URL = "https://remoteok.com/api"

# Keywords tailored to your background — same idea as adzuna.py/himalayas.py.
# RemoteOK's API doesn't support server-side keyword search, so we pull
# everything and filter on our side by checking these against the job
# title, tags, and description.
SEARCH_KEYWORDS = [
    "ai engineer",
    "machine learning",
    "llm",
    "rag",
    "computer vision",
    "python",
    "backend",
    "data scientist",
]


def fetch_remoteok() -> list[dict]:
    """
    Fetches remote jobs from RemoteOK's public API and filters them down
    to postings that match our target keywords.

    RemoteOK returns ALL of its current listings in one response (no
    pagination, no server-side search) — so this function does the
    keyword filtering itself instead of asking the API to do it.

    Returns a list of normalized posting dicts, ready for Supabase.
    """
    normalized = []

    print("  fetching from RemoteOK...")

    try:
        response = requests.get(
            REMOTEOK_URL,
            timeout=10,
            headers={"User-Agent": "JobHunter/1.0 (portfolio project; contact: you@example.com)"},
        )
        response.raise_for_status()
        jobs = response.json()

    except requests.RequestException as e:
        print(f"  remoteok error: {e}")
        return normalized

    # RemoteOK always puts a "legal notice" object as the very first item
    # in the response — it's not a real job, so we skip it.
    if jobs and isinstance(jobs[0], dict) and "legal" in jobs[0]:
        jobs = jobs[1:]

    print(f"  remoteok returned {len(jobs)} total listings — filtering by keyword...")

    matched_count = 0
    for job in jobs:
        if _matches_keywords(job):
            normalized.append(_normalize(job))
            matched_count += 1

    print(f"  remoteok: {matched_count} listings matched our keywords")

    return normalized


def _matches_keywords(job: dict) -> bool:
    """
    Checks whether a job's title, tags, or description mention any of
    our target keywords. Case-insensitive, simple substring match —
    good enough for a first filter (Phase 3 scoring does the real work).
    """
    position = (job.get("position") or "").lower()
    description = (job.get("description") or "").lower()
    tags = " ".join(job.get("tags") or []).lower()

    combined_text = f"{position} {tags} {description}"

    return any(keyword in combined_text for keyword in SEARCH_KEYWORDS)


def _normalize(job: dict) -> dict:
    """
    Maps a raw RemoteOK job object into your postings schema.
    Same shape as adzuna.py/himalayas.py so run_phase3.py doesn't need
    to know which source a posting came from.
    """
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    pay_range = None
    if salary_min and salary_max:
        pay_range = f"${int(salary_min):,}–${int(salary_max):,} USD/yr"

    # RemoteOK gives either "date" (ISO string) or "epoch" (unix timestamp)
    posted_at = None
    if job.get("date"):
        try:
            posted_at = dateparser.parse(job["date"]).isoformat()
        except Exception:
            pass

    # apply_url is the direct application link when present; url is the
    # RemoteOK listing page itself, used as a fallback.
    apply_link = job.get("apply_url") or job.get("url", "")

    return {
        "source": "remoteok",
        "kind": "job",
        "title": (job.get("position") or "").strip(),
        "company": job.get("company"),
        "description": (job.get("description") or "").strip(),
        "url": apply_link.strip(),
        "pay_range": pay_range,
        "location": job.get("location") or "Remote",
        "posted_at": posted_at,
    }

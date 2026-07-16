import os
import requests
from dateutil import parser as dateparser
from datetime import datetime, timezone

# Arbeitnow's public job board API — free, no API key required.
ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"

# Same idea as remoteok.py — Arbeitnow doesn't support keyword search
# server-side, so we page through results and filter locally.
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

# How many pages to walk before giving up. Each page is usually ~100
# jobs, so this is a reasonable ceiling without pulling in Arbeitnow's
# entire (non-AI-focused) job board.
MAX_PAGES = 5


def fetch_arbeitnow() -> list[dict]:
    """
    Fetches jobs from Arbeitnow's public API, walks through pages until
    either MAX_PAGES is hit or the API runs out of results, and filters
    down to postings matching our target keywords.

    Returns a list of normalized posting dicts, ready for Supabase.
    """
    normalized = []
    matched_count = 0
    total_seen = 0

    print("  fetching from Arbeitnow...")

    page = 1
    while page <= MAX_PAGES:
        try:
            response = requests.get(
                ARBEITNOW_URL,
                params={"page": page},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            jobs = payload.get("data", [])

        except requests.RequestException as e:
            print(f"  arbeitnow error on page {page}: {e}")
            break

        if not jobs:
            print(f"  arbeitnow page {page}: no more results, stopping")
            break

        total_seen += len(jobs)

        for job in jobs:
            if _matches_keywords(job):
                normalized.append(_normalize(job))
                matched_count += 1

        print(f"  arbeitnow page {page}: {len(jobs)} listings seen, "
              f"{matched_count} matched so far")

        page += 1

    print(f"  arbeitnow: {total_seen} total listings seen, "
          f"{matched_count} matched our keywords")

    return normalized


def _matches_keywords(job: dict) -> bool:
    """
    Checks the job title, tags, and description against our target
    keyword list. Also requires the job to actually be remote, since
    Arbeitnow lists on-site roles too and this pipeline is remote-first.
    """
    if not job.get("remote", False):
        return False

    title = (job.get("title") or "").lower()
    description = (job.get("description") or "").lower()
    tags = " ".join(job.get("tags") or []).lower()

    combined_text = f"{title} {tags} {description}"

    return any(keyword in combined_text for keyword in SEARCH_KEYWORDS)


def _normalize(job: dict) -> dict:
    """
    Maps a raw Arbeitnow job object into your postings schema.
    """
    # Arbeitnow doesn't return salary data in the free tier — pay_range
    # stays None here, same as it would for any source that lacks it.
    pay_range = None

    # created_at comes back as a unix timestamp (seconds), not a string —
    # different from Adzuna/Himalayas, so it needs its own conversion.
    posted_at = None
    if job.get("created_at"):
        try:
            posted_at = datetime.fromtimestamp(
                job["created_at"], tz=timezone.utc
            ).isoformat()
        except Exception:
            pass

    return {
        "source": "arbeitnow",
        "kind": "job",
        "title": (job.get("title") or "").strip(),
        "company": job.get("company_name"),
        "description": (job.get("description") or "").strip(),
        "url": (job.get("url") or "").strip(),
        "pay_range": pay_range,
        "location": job.get("location") or "Remote",
        "posted_at": posted_at,
    }

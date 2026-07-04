import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

REMOTIVE_BASE = "https://remotive.io/api/remote-jobs"

# Remotive uses fixed categories — these are the relevant ones for your profile
CATEGORIES = [
    "software-dev",
    "data",
    "automation"
]

KEYWORDS = [
    "AI",
    "machine learning",
    "LLM",
    "Python",
    "automation",
    "rag"
]


def fetch_remotive() -> list[dict]:
    """
    Fetches remote jobs from Remotive public API.
    No auth required. Filters by category then keyword-matches locally.
    Returns normalized posting dicts.
    """
    normalized = []
    seen_ids = set()  # deduplicate within this run

    for category in CATEGORIES:
        try:
            response = requests.get(
                REMOTIVE_BASE,
                params={"category": category, "limit": 100},
                timeout=10,
                headers={"User-Agent": "JobCopilot/1.0 (portfolio project)"},
            )
            response.raise_for_status()
            jobs = response.json().get("jobs", [])

            # Filter to only jobs mentioning our keywords
            relevant = [
                job for job in jobs
                if _is_relevant(job) and job.get("id") not in seen_ids
            ]

            for job in relevant:
                seen_ids.add(job.get("id"))
                normalized.append(_normalize(job))

            print(f"  remotive '{category}': {len(jobs)} total → {len(relevant)} relevant")

        except requests.RequestException as e:
            print(f"  remotive error '{category}': {e}")

    return normalized


def _is_relevant(job: dict) -> bool:
    """
    Checks if a job is relevant to your target roles.
    Remotive returns all jobs in a category so we filter client-side.
    """
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(kw.lower() in text for kw in KEYWORDS)


def _normalize(job: dict) -> dict:
    """
    Maps a raw Remotive job object into your postings schema.
    Remotive descriptions are HTML — we strip them to plain text.
    """
    # Strip HTML from description
    raw_html = job.get("description", "")
    clean_text = BeautifulSoup(raw_html, "html.parser").get_text(
        separator=" ", strip=True
    )

    # Salary — Remotive includes it as a string when available e.g. "$80k - $120k"
    pay_range = job.get("salary") or None

    # Published date
    posted_at = None
    if job.get("publication_date"):
        try:
            posted_at = dateparser.parse(job["publication_date"]).isoformat()
        except Exception:
            pass

    # Location — Remotive specifies region requirements
    location = job.get("candidate_required_location") or "Remote"

    return {
        "source": "remotive",
        "kind": "job",
        "title": job.get("title", "").strip(),
        "company": job.get("company_name"),
        "description": clean_text,
        "url": job.get("url", "").strip(),
        "pay_range": pay_range,
        "location": location,
        "posted_at": posted_at,
    }
import os
import requests
from dateutil import parser as dateparser

# Jobicy's public API — free, no API key required.
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"

# Jobicy organizes jobs by broad industry tags rather than free-text
# search, so instead of keywords we search across the tags that are
# actually relevant to an AI/ML background.
INDUSTRY_TAGS = [
    "data-science",
    "dev",
]

# Extra keyword filter applied on top of the industry tags, same as the
# other fetchers, so "dev" jobs that have nothing to do with AI/ML get
# filtered back out.
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

# Jobicy's API caps results per request — 50 is the practical max.
RESULTS_PER_TAG = 50


def fetch_jobicy() -> list[dict]:
    """
    Fetches jobs from Jobicy's public API, one industry tag at a time,
    then filters those down further by keyword.

    Returns a list of normalized posting dicts, ready for Supabase.
    """
    normalized = []
    matched_count = 0
    total_seen = 0

    print("  fetching from Jobicy...")

    for tag in INDUSTRY_TAGS:
        try:
            response = requests.get(
                JOBICY_URL,
                params={"count": RESULTS_PER_TAG, "tag": tag},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            jobs = payload.get("jobs", [])

        except requests.RequestException as e:
            print(f"  jobicy error for tag '{tag}': {e}")
            continue

        total_seen += len(jobs)

        tag_matches = 0
        for job in jobs:
            if _matches_keywords(job):
                normalized.append(_normalize(job))
                matched_count += 1
                tag_matches += 1

        print(f"  jobicy tag '{tag}': {len(jobs)} listings seen, "
              f"{tag_matches} matched")

    print(f"  jobicy: {total_seen} total listings seen, "
          f"{matched_count} matched our keywords")

    return normalized


def _matches_keywords(job: dict) -> bool:
    """
    Checks the job title and excerpt/description against our target
    keyword list, since the industry tag alone (e.g. "dev") is too
    broad to trust on its own.
    """
    title = (job.get("jobTitle") or "").lower()
    excerpt = (job.get("jobExcerpt") or "").lower()
    description = (job.get("jobDescription") or "").lower()

    combined_text = f"{title} {excerpt} {description}"

    return any(keyword in combined_text for keyword in SEARCH_KEYWORDS)


def _normalize(job: dict) -> dict:
    """
    Maps a raw Jobicy job object into your postings schema.
    """
    salary_min = job.get("annualSalaryMin")
    salary_max = job.get("annualSalaryMax")
    currency = job.get("salaryCurrency") or "USD"
    pay_range = None
    if salary_min and salary_max:
        pay_range = f"{int(salary_min):,}–{int(salary_max):,} {currency}/yr"

    posted_at = None
    if job.get("pubDate"):
        try:
            posted_at = dateparser.parse(job["pubDate"]).isoformat()
        except Exception:
            pass

    # Jobicy's full description field is sometimes empty — fall back to
    # the excerpt so we're not storing a blank posting.
    description = job.get("jobDescription") or job.get("jobExcerpt") or ""

    return {
        "source": "jobicy",
        "kind": "job",
        "title": (job.get("jobTitle") or "").strip(),
        "company": job.get("companyName"),
        "description": description.strip(),
        "url": (job.get("url") or "").strip(),
        "pay_range": pay_range,
        "location": job.get("jobGeo") or "Remote",
        "posted_at": posted_at,
    }

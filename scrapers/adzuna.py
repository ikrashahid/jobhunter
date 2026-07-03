import os
import requests
from dateutil import parser as dateparser

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

# Keywords tailored to your background
SEARCH_KEYWORDS = [
    "AI engineer Python",
    "machine learning engineer",
    "AI automation engineer",
    "data scientist",
    "LLM engineer",
    "computer vision engineer",
    "backend engineer"
]

# Markets to search — gb and us cover the most remote AI roles
MARKETS = ["gb", "us"]


def fetch_adzuna(pages: int = 2) -> list[dict]:
    """
    Fetches jobs from Adzuna across all keywords and markets.
    Returns a list of normalized posting dicts ready for Supabase.
    """
    normalized = []

    for market in MARKETS:
        for keyword in SEARCH_KEYWORDS:
            for page in range(1, pages + 1):
                url = f"https://api.adzuna.com/v1/api/jobs/{market}/search/{page}"
                params = {
                    "app_id": ADZUNA_APP_ID,
                    "app_key": ADZUNA_APP_KEY,
                    "what": keyword,
                    "what_or": "remote",  
                    "results_per_page": 20,
                    "content-type": "application/json"
                }

                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    results = response.json().get("results", [])

                    for job in results:
                        normalized.append(_normalize(job, market))

                    print(f"  adzuna [{market}] '{keyword}' page {page}: {len(results)} results")

                except requests.RequestException as e:
                    print(f"  adzuna error [{market}] '{keyword}' page {page}: {e}")

    return normalized


def _normalize(job: dict, market: str) -> dict:
    """
    Maps a raw Adzuna job object into your postings schema.
    Only fields that exist in your Supabase table are included.
    embedding is left out here — Phase 3 adds it.
    """
    salary_min = job.get("salary_min")
    salary_max = job.get("salary_max")
    pay_range = None
    if salary_min and salary_max:
        currency = "GBP" if market == "gb" else "USD"
        pay_range = f"{int(salary_min):,}–{int(salary_max):,} {currency}/yr"

    posted_at = None
    if job.get("created"):
        try:
            posted_at = dateparser.parse(job["created"]).isoformat()
        except Exception:
            pass

    return {
        "source": "adzuna",
        "kind": "job",
        "title": job.get("title", "").strip(),
        "company": job.get("company", {}).get("display_name"),
        "description": job.get("description", "").strip(),
        "url": job.get("redirect_url", "").strip(),
        "pay_range": pay_range,
        "location": job.get("location", {}).get("display_name"),
        "posted_at": posted_at,
    }
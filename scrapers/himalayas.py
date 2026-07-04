import os
import requests
from dateutil import parser as dateparser

HIMALAYAS_BASE = "https://himalayas.app/jobs/api"

# Himalayas supports keyword search — these map directly to your target roles
SEARCH_QUERIES = [
    "AI engineer Python",
    "machine learning engineer",
    "LLM engineer",
    "RAG engineer",
    "automation engineer",
    "computer vision engineer"
]

# maximum number of pages to fetch per query (Himalayas paginates results)
MAX_PAGES = 2

def fetch_himalayas() -> list[dict]:
    """
    Fetches remote jobs from Himalayas public API.
    No auth required. Returns normalized posting dicts.
    """
    normalized = []

    for query in SEARCH_QUERIES:
        for page in range(1, MAX_PAGES + 1):
            params = {
                "q": query,
                "limit": 10, # number of results per page
                "offset": (page - 1) * 10,
            }

            try:
                response = requests.get(
                    HIMALAYAS_BASE,
                    params=params,
                    timeout=10,
                    headers={"User-Agent": "JobCopilot/1.0 (portfolio project)"},
                )
                response.raise_for_status()
                data = response.json()
                jobs = data.get("jobs", [])

                if not jobs:
                    break  # no more pages for this query

                for job in jobs:
                    normalized.append(_normalize(job))

                print(f"  himalayas '{query}' page {page}: {len(jobs)} results")

            except requests.RequestException as e:
                print(f"  himalayas error '{query}' page {page}: {e}")
                break

    return normalized


def _normalize(job: dict) -> dict:
    """
    Maps a raw Himalayas job object into your postings schema.
    """
    # Salary — Himalayas returns min/max in USD when available
    pay_range = None
    salary_min = job.get("salaryMin")
    salary_max = job.get("salaryMax")
    if salary_min and salary_max:
        pay_range = f"${int(salary_min):,}–${int(salary_max):,} USD/yr"
    elif salary_min:
        pay_range = f"from ${int(salary_min):,} USD/yr"

    # Published date
    posted_at = None
    if job.get("publishedAt"):
        try:
            posted_at = dateparser.parse(job["publishedAt"]).isoformat()
        except Exception:
            pass

    # Company name lives inside a nested object
    company_name = None
    company = job.get("company")
    if isinstance(company, dict):
        company_name = company.get("name")
    elif isinstance(company, str):
        company_name = company

    return {
        "source": "himalayas",
        "kind": "job",
        "title": job.get("title", "").strip(),
        "company": company_name,
        "description": job.get("description", "").strip(),
        "url": job.get("applicationLink") or job.get("url", ""),
        "pay_range": pay_range,
        "location": "Remote",
        "posted_at": posted_at,
    }
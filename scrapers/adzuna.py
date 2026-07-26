import os
import requests
from dateutil import parser as dateparser

ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY")

SEARCH_KEYWORDS = [
    "AI engineer Python",
    "machine learning engineer",
    "AI automation engineer",
    "LLM engineer",
    "computer vision engineer",
    "backend engineer",
]

MARKETS = ["gb", "us"]

# Cache resolved URLs so we don't hit the same company twice
_resolved_cache: dict[str, str | None] = {}


def fetch_adzuna(pages: int = 2) -> list[dict]:
    """
    Fetches jobs from Adzuna for discovery, then replaces every Adzuna
    redirect URL with a direct company careers page URL that works from
    Pakistan. Jobs where no direct URL is found are skipped entirely.
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
                    "what_and": "remote",   # both keyword AND remote must appear
                    "results_per_page": 20,
                    "content-type": "application/json",
                }

                try:
                    response = requests.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    results = response.json().get("results", [])

                    kept = 0
                    for job in results:
                        company = (
                            job.get("company", {}).get("display_name") or ""
                        ).strip()
                        title = job.get("title", "").strip()

                        if not company or not title:
                            continue

                        # Try to find a direct URL that works from Pakistan
                        direct_url = _find_direct_url(company, title)

                        if direct_url:
                            normalized.append(_normalize(job, market, direct_url))
                            kept += 1
                        # If no direct URL found, skip this job entirely

                    print(
                        f"  adzuna [{market}] '{keyword}' page {page}: "
                        f"{len(results)} fetched → {kept} with direct URLs"
                    )

                except requests.RequestException as e:
                    print(
                        f"  adzuna error [{market}] '{keyword}' page {page}: {e}"
                    )

    return normalized


def _slugify(company: str) -> str:
    """Converts company name to a URL slug for ATS lookups."""
    return (
        company.lower()
        .replace(" ", "-")
        .replace(".", "")
        .replace(",", "")
        .replace("'", "")
        .replace("&", "and")
        .strip("-")
    )


def _title_matches(candidate_title: str, target_title: str) -> bool:
    """
    Checks if a job title is close enough to the target.
    Uses word overlap — at least half the target words must appear.
    """
    target_words = [
        w for w in target_title.lower().split()
        if len(w) > 3  # skip short words like 'and', 'for', 'the'
    ]
    if not target_words:
        return False
    matches = sum(1 for w in target_words if w in candidate_title.lower())
    return matches >= max(1, len(target_words) // 2)


def _check_greenhouse(company: str, job_title: str) -> str | None:
    """
    Checks the company's Greenhouse board for a matching job.
    Returns the direct application URL or None.
    """
    slug = _slugify(company)
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"

    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "JobCopilot/1.0"})
        if r.status_code != 200:
            return None

        jobs = r.json().get("jobs", [])
        for job in jobs:
            title = job.get("title", "")
            if _title_matches(title, job_title):
                return job.get("absolute_url") or job.get("url")

    except Exception:
        pass

    return None


def _check_lever(company: str, job_title: str) -> str | None:
    """
    Checks the company's Lever board for a matching job.
    Returns the direct hosted URL or None.
    """
    slug = _slugify(company)
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"

    try:
        r = requests.get(url, timeout=6, headers={"User-Agent": "JobCopilot/1.0"})
        if r.status_code != 200:
            return None

        jobs = r.json()
        if not isinstance(jobs, list):
            return None

        for job in jobs:
            title = job.get("text", "")
            if _title_matches(title, job_title):
                return job.get("hostedUrl") or job.get("applyUrl")

    except Exception:
        pass

    return None


def _check_ashby(company: str, job_title: str) -> str | None:
    """
    Checks the company's Ashby board for a matching job.
    Returns the direct job URL or None.
    """
    slug = _slugify(company)
    url = f"https://jobs.ashbyhq.com/api/non-user-graphql"

    try:
        payload = {
            "operationName": "ApiJobBoardWithTeams",
            "variables": {"organizationHostedJobsPageName": slug},
            "query": """
                query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) {
                  jobBoard: jobBoardWithTeams(
                    organizationHostedJobsPageName: $organizationHostedJobsPageName
                  ) {
                    jobPostings { title id }
                  }
                }
            """,
        }
        r = requests.post(url, json=payload, timeout=6)
        if r.status_code != 200:
            return None

        postings = (
            r.json()
            .get("data", {})
            .get("jobBoard", {})
            .get("jobPostings", [])
        )
        for posting in postings:
            if _title_matches(posting.get("title", ""), job_title):
                job_id = posting.get("id", "")
                return f"https://jobs.ashbyhq.com/{slug}/{job_id}"

    except Exception:
        pass

    return None


def _find_direct_url(company: str, job_title: str) -> str | None:
    """
    Tries Greenhouse, Lever, and Ashby in order to find a direct
    application URL that works from Pakistan.

    Results are cached per company name to avoid duplicate API calls
    when the same company appears across multiple keyword searches.
    """
    cache_key = f"{company.lower()}::{job_title.lower()}"
    if cache_key in _resolved_cache:
        return _resolved_cache[cache_key]

    # Try each ATS in order of likelihood for AI/tech companies
    direct_url = (
        _check_greenhouse(company, job_title)
        or _check_lever(company, job_title)
        or _check_ashby(company, job_title)
    )

    _resolved_cache[cache_key] = direct_url
    return direct_url


def _normalize(job: dict, market: str, direct_url: str) -> dict:
    """
    Maps a raw Adzuna job object into your postings schema.
    Uses the resolved direct URL instead of the Adzuna redirect.
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
        "url": direct_url,          # direct company URL, not Adzuna redirect
        "pay_range": pay_range,
        "location": job.get("location", {}).get("display_name"),
        "posted_at": posted_at,
    }
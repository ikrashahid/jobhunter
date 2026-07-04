import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import re

# We Work Remotely public RSS feeds by category
# These are stable URLs — no auth, no rate limiting
WWR_FEEDS = [
    {
        "url": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
        "label": "programming",
    },
    {
        "url": "https://weworkremotely.com/categories/remote-ai-jobs.rss",
        "label": "artificial intelligence","ai",
    }
]

KEYWORDS = ["python", "ai","rag", "ml", "machine learning", "llm", "langchain", "automation"]


def fetch_weworkremotely() -> list[dict]:
    """
    Parses We Work Remotely RSS feeds.
    Filters entries by keyword relevance.
    Returns normalized posting dicts.
    """
    normalized = []

    for feed_info in WWR_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            entries = feed.entries

            relevant = [e for e in entries if _is_relevant(e)]

            for entry in relevant:
                normalized.append(_normalize(entry))

            print(
                f"  weworkremotely '{feed_info['label']}': "
                f"{len(entries)} total → {len(relevant)} relevant"
            )

        except Exception as e:
            print(f"  weworkremotely error '{feed_info['label']}': {e}")

    return normalized


def _is_relevant(entry) -> bool:
    """
    Checks title and summary for target keywords.
    """
    text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
    return any(kw in text for kw in KEYWORDS)


def _normalize(entry) -> dict:
    """
    Maps a raw WWR RSS entry into your postings schema.
    """
    # Strip HTML from summary
    raw_html = entry.get("summary", "")
    clean_text = BeautifulSoup(raw_html, "html.parser").get_text(
        separator=" ", strip=True
    )

    # WWR title format is usually "CompanyName: Job Title"
    raw_title = entry.get("title", "")
    company, title = _split_title(raw_title)

    # Try to extract salary from description
    pay_range = _extract_salary(clean_text)

    # Published date
    posted_at = None
    if entry.get("published"):
        try:
            posted_at = dateparser.parse(entry.published).isoformat()
        except Exception:
            pass

    # WWR link sometimes has the region appended — clean it
    url = entry.get("link", "").split("?")[0].strip()

    return {
        "source": "weworkremotely",
        "kind": "job",
        "title": title,
        "company": company,
        "description": clean_text,
        "url": url,
        "pay_range": pay_range,
        "location": "Remote",
        "posted_at": posted_at,
    }


def _split_title(raw: str) -> tuple[str, str]:
    """
    WWR RSS titles come as "Company: Job Title" or just "Job Title".
    Splits into (company, title).
    """
    if ":" in raw:
        parts = raw.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return None, raw.strip()


def _extract_salary(text: str) -> str | None:
    """
    Looks for salary patterns in the description text.
    """
    patterns = [
        r"\$[\d,]+\s*[-–]\s*\$[\d,]+",      # $80,000 - $120,000
        r"\$[\d]+k\s*[-–]\s*\$?[\d]+k",      # $80k - $120k
        r"[\d,]+\s*[-–]\s*[\d,]+\s*USD",     # 80,000 - 120,000 USD
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None
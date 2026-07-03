import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
import re


# Upwork RSS URLs for your target gig categories
UPWORK_FEEDS = [
    "https://www.upwork.com/ab/feed/jobs/rss?q=AI+engineer+Python&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=machine+learning+engineer&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=LLM+langchain+python&sort=recency",
    "https://www.upwork.com/ab/feed/jobs/rss?q=computer+vision+python&sort=recency",
]


def fetch_upwork() -> list[dict]:
    """
    Parses all Upwork RSS feeds.
    Returns a list of normalized posting dicts ready for Supabase.
    """
    normalized = []

    for feed_url in UPWORK_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries

            for entry in entries:
                normalized.append(_normalize(entry))

            print(f"  upwork '{feed_url.split('q=')[1].split('&')[0]}': {len(entries)} results")

        except Exception as e:
            print(f"  upwork error '{feed_url}': {e}")

    return normalized


def _normalize(entry) -> dict:
    """
    Maps a raw Upwork RSS entry into your postings schema.
    """
    # Strip HTML from description
    raw_html = entry.get("summary", "")
    clean_text = BeautifulSoup(raw_html, "html.parser").get_text(separator=" ").strip()

    # Try to extract budget from description text
    pay_range = _extract_budget(clean_text)

    posted_at = None
    if entry.get("published"):
        try:
            posted_at = dateparser.parse(entry.published).isoformat()
        except Exception:
            pass

    return {
        "source": "upwork",
        "kind": "gig",
        "title": entry.get("title", "").strip(),
        "company": None,        # gigs don't have a company
        "description": clean_text,
        "url": entry.get("link", "").strip(),
        "pay_range": pay_range,
        "location": "Remote",   # Upwork is always remote
        "posted_at": posted_at,
    }


def _extract_budget(text: str) -> str | None:
    """
    Tries to pull a budget figure out of the Upwork description text.
    Upwork includes lines like "Budget: $500" or "Hourly Range: $25-$50"
    """
    budget_match = re.search(r"Budget:\s*\$?([\d,]+)", text)
    if budget_match:
        return f"${budget_match.group(1)} fixed"

    hourly_match = re.search(r"Hourly Range:\s*\$?([\d.]+)-\$?([\d.]+)", text)
    if hourly_match:
        return f"${hourly_match.group(1)}–${hourly_match.group(2)}/hr"

    return None
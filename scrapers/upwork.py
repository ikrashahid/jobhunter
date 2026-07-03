"""
Upwork job search scraper using Selenium.

SETUP (one-time):
1. pip install selenium webdriver-manager beautifulsoup4 python-dateutil
2. Run this script once with HEADLESS = False (below).
   A Chrome window will open to Upwork. Log into your account manually.
   Your session will be saved to the CHROME_PROFILE_DIR folder.
3. On future runs, Selenium reuses that saved login - no need to log in again,
   unless the session expires or Upwork logs you out.

IMPORTANT:
- Scraping logged-in Upwork pages is outside Upwork's Terms of Service.
  Use conservative delays, don't run this constantly, and understand the
  risk of account flags/suspension falls on the account you're logged into.
- Selectors below are a best-effort starting point. Upwork's front-end HTML
  changes over time - if you get 0 results, open DevTools on the search
  results page and update the SELECTORS dict to match current class names.
"""

import time
import random
import re
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dateutil import parser as dateparser


class CheckpointDetected(Exception):
    """Raised when Upwork shows a CAPTCHA/verification page instead of content."""
    pass


# ---- Config ----

CHROME_PROFILE_DIR = str(Path.home() / ".upwork_scraper_profile")
HEADLESS = False  # set True once you've confirmed login works and selectors are correct

SEARCH_QUERIES = [
    "AI engineer Python",
    "machine learning engineer",
    "LLM langchain python",
    "computer vision python",
]

# Base search URL - &sort=recency keeps newest jobs first
SEARCH_URL_TEMPLATE = "https://www.upwork.com/nx/search/jobs/?q={query}&sort=recency"

# CSS selectors - VERIFY THESE against the live page via DevTools before relying on this
SELECTORS = {
    "job_card": "section[data-test='job-tile-list'] article, div[data-test='JobTile']",
    "title": "a[data-test='job-title-link'], h2 a",
    "description": "div[data-test='job-description-text'], span[data-test='job-description-text']",
    "budget": "li[data-test='is-fixed-price'], li[data-test='duration-label'], span[data-test='budget']",
    "posted_time": "span[data-test='posted-on'], small[data-test='posted-on']",
}


def build_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_DIR}")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1400,1000")

    driver = webdriver.Chrome(options=options)
    # Hide the obvious "navigator.webdriver" automation flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def human_delay(a=1.5, b=3.5):
    """Sleep a random amount. Occasionally throw in a longer pause,
    like a person who got distracted reading a job post."""
    time.sleep(random.uniform(a, b))
    if random.random() < 0.15:  # ~15% of the time, pause longer
        time.sleep(random.uniform(2.0, 5.0))


def check_for_checkpoint(driver: webdriver.Chrome):
    """
    Bail out (rather than try to push through) if Upwork shows a
    CAPTCHA, phone verification, or other checkpoint page.
    """
    page_text = driver.page_source.lower()
    checkpoint_markers = ["verify you are human", "captcha", "unusual activity", "checkpoint"]
    if any(marker in page_text for marker in checkpoint_markers):
        raise CheckpointDetected(
            "Upwork is showing a verification/CAPTCHA page. Stopping the script - "
            "please resolve this manually in the browser window."
        )


def ensure_logged_in(driver: webdriver.Chrome):
    """
    Navigates to Upwork and checks whether we're logged in.
    If not, pauses and waits for you to log in manually.
    """
    driver.get("https://www.upwork.com/nx/find-work/")
    human_delay(2, 3)

    if "login" in driver.current_url.lower():
        print("\n*** Not logged in. A browser window is open. ***")
        print("*** Please log into Upwork manually now. ***")
        input("Press Enter here once you're logged in and see the job feed... ")


def natural_scroll(driver: webdriver.Chrome, passes: int = None):
    """
    Scrolls down in irregular steps, occasionally pausing or nudging back up -
    closer to how someone actually reads a results page than a fixed loop.
    """
    passes = passes or random.randint(3, 6)
    for _ in range(passes):
        distance = random.randint(250, 900)
        driver.execute_script(f"window.scrollBy(0, {distance});")
        human_delay(0.6, 1.8)

        # Occasionally scroll back up slightly, like re-reading something
        if random.random() < 0.2:
            driver.execute_script(f"window.scrollBy(0, {-random.randint(100, 300)});")
            human_delay(0.4, 1.0)


def hover_element(driver: webdriver.Chrome, element):
    """Move the mouse over an element before interacting with it."""
    try:
        ActionChains(driver).move_to_element(element).pause(random.uniform(0.3, 0.9)).perform()
    except Exception:
        pass  # non-critical - if hover fails, just continue


def scrape_query(driver: webdriver.Chrome, query: str) -> list[dict]:
    url = SEARCH_URL_TEMPLATE.format(query=query.replace(" ", "+"))
    driver.get(url)
    human_delay(1.5, 3.0)
    check_for_checkpoint(driver)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SELECTORS["job_card"]))
        )
    except Exception:
        print(f"  '{query}': no job cards found (selector may be outdated, or 0 results)")
        return []

    natural_scroll(driver)

    # Hover a job card or two before reading, like a person skimming the page
    try:
        visible_cards = driver.find_elements(By.CSS_SELECTOR, SELECTORS["job_card"])
        for el in random.sample(visible_cards, k=min(2, len(visible_cards))):
            hover_element(driver, el)
    except Exception:
        pass

    check_for_checkpoint(driver)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select(SELECTORS["job_card"])
    print(f"  '{query}': {len(cards)} job cards found")

    results = []
    for card in cards:
        results.append(_parse_card(card))

    return results


def _parse_card(card) -> dict:
    title_el = card.select_one(SELECTORS["title"])
    desc_el = card.select_one(SELECTORS["description"])
    budget_el = card.select_one(SELECTORS["budget"])
    posted_el = card.select_one(SELECTORS["posted_time"])

    title = title_el.get_text(strip=True) if title_el else None
    link = title_el.get("href") if title_el else None
    if link and link.startswith("/"):
        link = "https://www.upwork.com" + link

    description = desc_el.get_text(separator=" ", strip=True) if desc_el else ""
    budget_text = budget_el.get_text(strip=True) if budget_el else ""
    posted_text = posted_el.get_text(strip=True) if posted_el else ""

    posted_at = None
    if posted_text:
        try:
            posted_at = dateparser.parse(posted_text, fuzzy=True).isoformat()
        except Exception:
            posted_at = None  # relative times like "2 hours ago" won't parse cleanly - handle separately if needed

    return {
        "source": "upwork",
        "kind": "gig",
        "title": title,
        "company": None,
        "description": description,
        "url": link,
        "pay_range": budget_text or _extract_budget(description),
        "location": "Remote",
        "posted_at": posted_at,
        "posted_raw": posted_text,
    }


def _extract_budget(text: str) -> str | None:
    budget_match = re.search(r"Budget:\s*\$?([\d,]+)", text)
    if budget_match:
        return f"${budget_match.group(1)} fixed"

    hourly_match = re.search(r"Hourly Range:\s*\$?([\d.]+)-\$?([\d.]+)", text)
    if hourly_match:
        return f"${hourly_match.group(1)}\u2013${hourly_match.group(2)}/hr"

    return None


def fetch_upwork() -> list[dict]:
    driver = build_driver()
    all_results = []

    # Randomize order each run instead of always hitting queries in the same sequence
    queries = SEARCH_QUERIES.copy()
    random.shuffle(queries)

    try:
        ensure_logged_in(driver)

        for query in queries:
            try:
                results = scrape_query(driver, query)
                all_results.extend(results)
            except CheckpointDetected as e:
                print(f"\n  {e}")
                print("  Stopping the run here rather than continuing past a checkpoint.")
                break
            except Exception as e:
                print(f"  error scraping '{query}': {e}")

            # Wider, more irregular pause between searches
            time.sleep(random.uniform(4, 11))

    finally:
        driver.quit()

    return all_results


if __name__ == "__main__":
    postings = fetch_upwork()
    print(f"\nTotal postings scraped: {len(postings)}")
    for p in postings[:5]:
        print(f"  - {p['title']} | {p['pay_range']} | {p['url']}")
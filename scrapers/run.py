from dotenv import load_dotenv
load_dotenv()

from adzuna import fetch_adzuna
from upwork import fetch_upwork
from store import store_postings


def run():
    print("\n── Job + Gig Copilot: Fetching ──\n")

    # Fetch from both sources
    print("Adzuna jobs:")
    jobs = fetch_adzuna(pages=2)
    print("total jobs fetched:", len(jobs))
    

    print("\nUpwork gigs:")
    gigs = fetch_upwork()

    all_postings = jobs + gigs
    print(f"\nTotal fetched: {len(all_postings)} ({len(jobs)} jobs, {len(gigs)} gigs)")

    # # # Store everything
    print("\nStoring to Supabase...")
    result = store_postings(all_postings)
    print(f"Inserted: {result['inserted']}  Skipped (duplicates): {result['skipped']}")

    # print("\n── Done ──\n")


if __name__ == "__main__":
    run()
from dotenv import load_dotenv
load_dotenv()

from adzuna import fetch_adzuna
from upwork import fetch_upwork
from storejob import store_postings


def run():
    print("\n── Job + Gig Copilot: Fetching ──\n")

    # Fetch from both sources
    print("Adzuna jobs:")
    jobs = fetch_adzuna(pages=2)
    print("total jobs fetched:", len(jobs))
    

    # print("\nUpwork gigs:")
    # gigs = fetch_upwork()
    # print("total gigs fetched:", len(gigs))

    # all_postings = jobs + gigs
    # print(f"\nTotal fetched: {len(all_postings)} ({len(jobs)} jobs, {len(gigs)} gigs)")

    # # Store everything
    print("\nStoring to Supabase...")
    result = store_postings(jobs)
    print(
    f"Inserted: {result['inserted']} | "
    f"Duplicates: {result['duplicates']} | "
    f"Empty URLs: {result['empty_urls']}")

    print("\n── Done ──\n")


if __name__ == "__main__":
    run()
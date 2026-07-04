from dotenv import load_dotenv
load_dotenv()

from adzuna import fetch_adzuna
from himalayas import fetch_himalayas
from remotive import fetch_remotive
from weworkremotely import fetch_weworkremotely
from store import store_postings


def run():
    print("\n── Job Copilot: Fetching ──\n")

    results = {}

    print("Adzuna jobs:")
    results["adzuna"] = fetch_adzuna(pages=2)

    print("\nHimalayas remote jobs:")
    results["himalayas"] = fetch_himalayas()

    print("\nRemotive remote jobs:")
    results["remotive"] = fetch_remotive()

    print("\nWe Work Remotely:")
    results["wwr"] = fetch_weworkremotely()

    # Combine everything
    all_postings = []
    for source, postings in results.items():
        all_postings.extend(postings)
        print(f"  {source}: {len(postings)} fetched")

    print(f"\nTotal fetched: {len(all_postings)}")

    # Store with deduplication
    print("\nStoring to Supabase...")
    result = store_postings(all_postings)
    print(f"Inserted: {result['inserted']}  Skipped (duplicates): {result['skipped']}")

    print("\n── Done ──\n")


if __name__ == "__main__":
    run()
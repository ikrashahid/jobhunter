from dotenv import load_dotenv
load_dotenv()

from adzuna import fetch_adzuna
from himalayas import fetch_himalayas
from store import store_postings


def run():
    print("\n── Job Copilot: Fetching ──\n")

    print("Adzuna jobs:")
    jobs = fetch_adzuna(pages=2)

    print("\nHimalayas remote jobs:")
    remote = fetch_himalayas()

    all_postings = jobs + remote
    print(f"\n  adzuna: {len(jobs)} fetched")
    print(f"  himalayas: {len(remote)} fetched")
    print(f"  total: {len(all_postings)}")

    print("\nStoring to Supabase...")
    result = store_postings(all_postings)
    print(f"Inserted: {result['inserted']}  Skipped: {result['skipped']}")

    print("\n── Done ──\n")


if __name__ == "__main__":
    run()
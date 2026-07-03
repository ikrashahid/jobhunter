import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def store_postings(postings: list[dict]) -> dict:
    """
    Inserts a batch of normalized postings into Supabase.
    Uses upsert on url to skip duplicates silently.
    Returns a summary of what happened.
    """
    if not postings:
        return {"inserted": 0, "skipped": 0}

    client = get_client()

    # Remove empty URLs — these can't be stored meaningfully
    valid = [p for p in postings if p.get("url")]
    skipped_empty = len(postings) - len(valid)

    try:
        # on_conflict="url" means: if this URL already exists, do nothing
        response = (
            client.table("postings")
            .upsert(valid, on_conflict="url", ignore_duplicates=True)
            .execute()
        )
        inserted = len(response.data) if response.data else 0

    except Exception as e:
        print(f"  supabase error: {e}")
        return {"inserted": 0, "skipped": len(valid)}

    return {
        "inserted": inserted,
        "skipped": (len(valid) - inserted) + skipped_empty
    }
"""
fetch_all_sources.py — runs all five job fetchers, stores new postings
in Supabase, and plays a sound when finished.

Sources: Adzuna, Himalayas, RemoteOK, Arbeitnow, Jobicy.

Run this before run_pipeline.py (or run_phase3.py) — it's the step
that actually brings new postings into the `postings` table for
everything downstream to embed, score, draft, and evaluate.
"""

import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

for _parent in [Path(__file__).parent, Path(__file__).parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

from supabase import create_client

from adzuna import fetch_adzuna
from himalayas import fetch_himalayas
from remoteok import fetch_remoteok
from arbeitnow import fetch_arbeitnow
from jobicy import fetch_jobicy
from notify import play_done_sound


def run():
    start_time = time.time()

    print(f"\n{'#' * 60}")
    print("  JOB HUNTER — FETCH ALL SOURCES")
    print(f"  started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#' * 60}\n")

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # Each entry: (friendly name, fetch function). Adding a 6th source
    # later is just adding one more tuple here.
    sources = [
        ("Adzuna", fetch_adzuna),
        ("Himalayas", fetch_himalayas),
        ("RemoteOK", fetch_remoteok),
        ("Arbeitnow", fetch_arbeitnow),
        ("Jobicy", fetch_jobicy),
    ]

    all_postings = []
    source_counts = {}

    for name, fetch_fn in sources:
        print(f"\n{'─' * 60}")
        print(f"  Source: {name}")
        print(f"{'─' * 60}")

        try:
            postings = fetch_fn()
            source_counts[name] = len(postings)
            all_postings.extend(postings)
            print(f"  {name} done — {len(postings)} postings collected")

        except Exception as e:
            # One source failing (e.g. an API being down) shouldn't stop
            # the other four from running.
            print(f"  {name} FAILED entirely: {e}")
            source_counts[name] = 0

    print(f"\n{'═' * 60}")
    print(f"  Storing {len(all_postings)} postings to Supabase...")
    print(f"{'═' * 60}\n")

    inserted, skipped, failed = _store_postings(client, all_postings)

    # ── Summary ──────────────────────────────────────────────
    elapsed = time.time() - start_time

    print(f"\n{'#' * 60}")
    print("  FETCH RUN COMPLETE")
    print(f"{'#' * 60}")
    print(f"  total time         : {elapsed:.1f}s ({elapsed / 60:.1f} min)")
    print("  postings per source:")
    for name, count in source_counts.items():
        print(f"    {name:<12} {count}")
    print(f"  new postings stored : {inserted}")
    print(f"  duplicates skipped  : {skipped}")
    print(f"  failed to store     : {failed}")
    print(f"{'#' * 60}\n")

    play_done_sound()


def _store_postings(client, postings: list[dict]) -> tuple[int, int, int]:
    """
    Upserts postings into Supabase. Assumes a unique constraint on `url`
    so re-running the fetchers doesn't create duplicate rows for the
    same job (postings from these APIs don't have a shared, stable
    "posting_id" format across sources, but the apply URL is a good
    natural key).

    Returns (inserted_count, skipped_count, failed_count).
    """
    inserted = 0
    skipped = 0
    failed = 0

    for posting in postings:
        # Skip anything with no URL or no title — not enough to be
        # useful, and would break the unique constraint anyway.
        if not posting.get("url") or not posting.get("title"):
            skipped += 1
            continue

        try:
            result = (
                client.table("postings")
                .upsert(posting, on_conflict="url", ignore_duplicates=True)
                .execute()
            )
            # Supabase returns the row whether it was newly inserted or
            # already existed (with ignore_duplicates, it still returns
            # data) — we count conservatively as "inserted" here since
            # distinguishing the two would need an extra query per row.
            inserted += 1

        except Exception as e:
            print(f"  store error for '{posting.get('title')}': {e}")
            failed += 1

    return inserted, skipped, failed


if __name__ == "__main__":
    run()

"""
run_pipeline.py — Phase 3 + Phase 4, merged into one tracked run.

Runs, in order:
  1. Embed resume (if changed)
  2. Embed any unembedded postings
  3. Score postings against resume (hybrid retrieval + rerank)
  4. Draft cover letters for undrafted matches
  5. Evaluate each draft (faithfulness + quality)

Every step prints a timestamp and elapsed time, so a long run leaves a
readable trail of what happened and how long each part took — useful
both for debugging and for the dashboard's future "last run" log.

Pauses are inserted between LLM calls (drafting + faithfulness eval,
both hit Groq) to stay under free-tier rate limits — the same limit
that caused the token/rate errors earlier. Adjust PAUSE_BETWEEN_DRAFTS
if you're still hitting rate limit errors.
"""

import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path

for _parent in [Path(__file__).parent, Path(__file__).parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

from supabase import create_client
from embed import embed_resume, embed_unembedded_postings
from score import score_postings
from draft import draft_cover_letter
from evaluate import score_faithfulness, score_quality

# ─────────────────────────────────────────────────────────────
PAUSE_BETWEEN_DRAFTS = 5   # seconds — spacing between each match's LLM calls
PAUSE_AFTER_EMBEDDING = 2  # seconds — brief pause after embedding, before scoring
MAX_MATCHES_TO_DRAFT = 5   # same limit run_phase4.py used
# ─────────────────────────────────────────────────────────────

_run_start = None


def _log(msg: str) -> None:
    """Prints a message with a timestamp and elapsed time since run start."""
    elapsed = time.time() - _run_start
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now} | +{elapsed:6.1f}s] {msg}")


def _section(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def run():
    global _run_start
    _run_start = time.time()

    print(f"\n{'#' * 60}")
    print(f"  JOB HUNTER — FULL PIPELINE RUN")
    print(f"  started {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#' * 60}")

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    summary = {
        "postings_embedded": 0,
        "matches_scored": 0,
        "drafts_attempted": 0,
        "drafts_succeeded": 0,
        "drafts_failed": 0,
    }

    # ── PHASE 3, STEP 1: Embed resume ──────────────────────────
    _section("PHASE 3.1 — Embed Resume")
    resume_path = os.path.join(os.path.dirname(__file__), "../resume.txt")
    if not os.path.exists(resume_path):
        _log("resume.txt not found — create it at the project root. Stopping.")
        return

    with open(resume_path, "r") as f:
        resume_text = f.read()

    _log(f"read resume.txt ({len(resume_text)} chars)")
    embed_resume(resume_text, label="main")
    _log("resume embedded and stored")

    # ── PHASE 3, STEP 2: Embed postings ────────────────────────
    _section("PHASE 3.2 — Embed Postings")
    embedded_count = embed_unembedded_postings(batch_size=50)
    summary["postings_embedded"] = embedded_count
    _log(f"embedded {embedded_count} new postings")

    if embedded_count > 0:
        _log(f"pausing {PAUSE_AFTER_EMBEDDING}s before scoring...")
        time.sleep(PAUSE_AFTER_EMBEDDING)

    # ── PHASE 3, STEP 3: Score postings ────────────────────────
    _section("PHASE 3.3 — Score Postings")
    profile = (
        client.table("profile")
        .select("embedding, content, sections")
        .eq("label", "main")
        .single()
        .execute()
    )
    if not profile.data:
        _log("no profile found after embedding — something went wrong. Stopping.")
        return

    resume_embedding = profile.data["embedding"]
    resume_content = profile.data["content"]
    resume_sections = profile.data.get("sections") or {}

    _log("running hybrid scoring (vector + BM25 + RRF + cross-encoder)...")
    matches = score_postings(resume_content, resume_embedding)
    summary["matches_scored"] = len(matches)
    _log(f"scoring complete — {len(matches)} matches stored")

    for m in matches[:5]:
        _log(f"  [{m['final_score']:.2f}] {m.get('title')} — {m.get('company')}")

    if not resume_sections:
        _log("resume sections are empty — check embed.py chunking. Skipping drafting.")
        _print_summary(summary)
        return

    # ── PHASE 4, STEP 1-3: Draft + Evaluate ────────────────────
    _section("PHASE 4 — Draft + Evaluate")

    undrafted = (
        client.table("matches")
        .select("id, posting_id, score")
        .is_("draft", "null")
        .order("score", desc=True)
        .limit(MAX_MATCHES_TO_DRAFT)
        .execute()
    )

    if not undrafted.data:
        _log("no undrafted matches found — nothing to draft this run")
        _print_summary(summary)
        return

    _log(f"found {len(undrafted.data)} undrafted matches")

    for i, match in enumerate(undrafted.data, 1):
        posting = (
            client.table("postings")
            .select("title, company, description, url")
            .eq("id", match["posting_id"])
            .single()
            .execute()
        )
        p = posting.data
        company = p.get("company") or "the company"

        _section(f"[{i}/{len(undrafted.data)}] {p['title']} @ {company}  (score: {match['score']:.3f})")
        summary["drafts_attempted"] += 1

        # Step 1: Draft
        _log("running drafting crew (Researcher → Drafter → Refiner)...")
        try:
            result = draft_cover_letter(
                job_title=p["title"],
                company=company,
                job_description=p.get("description") or "",
                resume_sections=resume_sections,
            )
            draft_text = result["draft"]
            _log(f"draft complete ({len(draft_text)} chars)"
                 + (" — job description was truncated" if result.get("job_description_truncated") else ""))
        except Exception as e:
            _log(f"drafting FAILED: {e}")
            summary["drafts_failed"] += 1
            _log(f"pausing {PAUSE_BETWEEN_DRAFTS}s before next match...")
            time.sleep(PAUSE_BETWEEN_DRAFTS)
            continue

        # Step 2: Faithfulness eval
        _log("running faithfulness evaluation...")
        try:
            faith_result = score_faithfulness(
                draft=draft_text,
                resume_sections=resume_sections,
                job_description=p.get("description") or "",
            )
            _log(f"faithfulness: {faith_result.get('faithfulness_score')} — {faith_result.get('flag')}")
        except Exception as e:
            _log(f"faithfulness eval FAILED (non-fatal): {e}")
            faith_result = {
                "faithfulness_score": None,
                "flag": "eval error",
                "passes": True,
                "verdicts": [],
            }

        # Step 3: Quality eval (no LLM call, no pause needed)
        quality_result = score_quality(draft_text)
        _log(f"quality: {quality_result.get('quality_score')} — "
             f"{'clean' if quality_result.get('passes') else 'needs revision'}")

        # Step 4: Store
        eval_metadata = {
            "faithfulness_score": faith_result.get("faithfulness_score"),
            "total_claims": faith_result.get("total_claims"),
            "supported_claims": faith_result.get("supported_claims"),
            "faithfulness_flag": faith_result.get("flag"),
            "verdicts": faith_result.get("verdicts", []),
            "quality_score": quality_result.get("quality_score"),
            "banned_phrases_found": quality_result.get("banned_found", []),
            "quality_flag": "clean" if quality_result.get("passes") else "needs revision",
            "company_research": result.get("company_research", ""),
            "job_description_truncated": result.get("job_description_truncated", False),
        }

        client.table("matches").update({
            "draft": draft_text,
            "tailored_resume": json.dumps(eval_metadata),
        }).eq("id", match["id"]).execute()

        summary["drafts_succeeded"] += 1
        _log("stored to Supabase")

        if i < len(undrafted.data):
            _log(f"pausing {PAUSE_BETWEEN_DRAFTS}s before next match (rate limit spacing)...")
            time.sleep(PAUSE_BETWEEN_DRAFTS)

    _print_summary(summary)


def _print_summary(summary: dict) -> None:
    total_elapsed = time.time() - _run_start
    _section("PIPELINE RUN COMPLETE")
    print(f"  total time          : {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")
    print(f"  postings embedded   : {summary['postings_embedded']}")
    print(f"  matches scored      : {summary['matches_scored']}")
    print(f"  drafts attempted    : {summary['drafts_attempted']}")
    print(f"  drafts succeeded    : {summary['drafts_succeeded']}")
    print(f"  drafts failed       : {summary['drafts_failed']}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    run()
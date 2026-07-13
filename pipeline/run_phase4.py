from dotenv import load_dotenv
from pathlib import Path

# Load .env from project root regardless of where you run from
load_dotenv(Path(__file__).parent.parent / ".env")
import os
import json
from supabase import create_client
from draft import draft_cover_letter
from evaluate import score_faithfulness


def run():
    print("\n── Phase 4: Draft + Evaluate ──\n")

    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

    # ── Load resume sections from profile table ──
    profile = (
        client.table("profile")
        .select("sections, content")
        .eq("label", "main")
        .single()
        .execute()
    )

    if not profile.data:
        print("  no profile found — run phase 3 first")
        return

    resume_sections = profile.data.get("sections") or {}

    if not resume_sections:
        print("  resume sections are empty — check embed.py chunking")
        return

    print(f"  loaded {len(resume_sections)} resume sections: {list(resume_sections.keys())}")

    # ── Fetch top undrafted matches ──
    matches = (
        client.table("matches")
        .select("id, posting_id, score")
        .is_("draft", "null")
        .order("score", desc=True)
        .limit(5)
        .execute()
    )

    if not matches.data:
        print("  no undrafted matches — either all drafted or matches table is empty")
        return

    print(f"  found {len(matches.data)} undrafted matches\n")

    for i, match in enumerate(matches.data, 1):

        # ── Fetch posting details ──
        posting = (
            client.table("postings")
            .select("title, company, description, url")
            .eq("id", match["posting_id"])
            .single()
            .execute()
        )
        p = posting.data
        company = p.get("company") or "the company"

        print(f"\n{'═'*55}")
        print(f"  [{i}/{len(matches.data)}] {p['title']} @ {company}")
        print(f"  match score: {match['score']:.3f}")
        print(f"{'═'*55}")

        # ── Step 1: Draft ──
        print("\n  running drafting crew...")
        try:
            result = draft_cover_letter(
                job_title=p["title"],
                company=company,
                job_description=p.get("description") or "",
                resume_sections=resume_sections,
            )
            draft_text = result["draft"]
            print(f"  draft complete ({len(draft_text)} chars)")
        except Exception as e:
            print(f"  drafting failed: {e}")
            continue

        # ── Step 2: Faithfulness eval ──
        print("\n  running faithfulness evaluation...")
        try:
            eval_result = score_faithfulness(
                draft=draft_text,
                resume_sections=resume_sections,
                job_description=p.get("description") or "",
            )
        except Exception as e:
            print(f"  eval failed: {e}")
            eval_result = {
                "faithfulness_score": None,
                "flag": "eval error",
                "passes": True,
                "verdicts": [],
            }

        # ── Step 3: Store back to Supabase ──
        eval_metadata = {
            "faithfulness_score": eval_result.get("faithfulness_score"),
            "total_claims": eval_result.get("total_claims"),
            "supported_claims": eval_result.get("supported_claims"),
            "flag": eval_result.get("flag"),
            "verdicts": eval_result.get("verdicts", []),
            "company_research": result.get("company_research", ""),
        }

        client.table("matches").update({
            "draft": draft_text,
            "tailored_resume": json.dumps(eval_metadata),
        }).eq("id", match["id"]).execute()

        print(f"  stored to Supabase")

        # ── Print the draft ──
        print(f"\n{'─'*55}")
        print(f"COVER LETTER — {p['title']} @ {company}")
        print(f"{'─'*55}")
        print(draft_text)
        print(f"{'─'*55}")
        print(f"Faithfulness: {eval_result.get('faithfulness_score', 'N/A')} — {eval_result.get('flag')}")

    print("\n\n── Phase 4 Done ──\n")


if __name__ == "__main__":
    run()
import os
import json
from dotenv import load_dotenv
from pathlib import Path

for _parent in [Path(__file__).parent, Path(__file__).parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

from supabase import create_client
from draft import draft_cover_letter
from evaluate import score_faithfulness, score_quality

def estimate_tokens(text: str) -> int:
    # rough estimate: 1 token ≈ 4 chars for English
    return len(text) // 4

def will_exceed_limit(job_desc: str, resume: str, buffer: int = 1000) -> bool:
    # prompt overhead ~500 tokens, buffer for safety
    total = estimate_tokens(job_desc) + estimate_tokens(resume) + 500 + buffer
    return total > 5500  # Groq free tier safe limit
def run():
    print("\n── Phase 4: Draft + Evaluate ──\n")

    client = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

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

    matches = (
        client.table("matches")
        .select("id, posting_id, score")
        .is_("draft", "null")
        .order("score", desc=True)
        .limit(5)
        .execute()
    )

    if not matches.data:
        print("  no undrafted matches found")
        return

    print(f"  found {len(matches.data)} undrafted matches\n")

    for i, match in enumerate(matches.data, 1):
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
        # In run_phase4.py, before calling draft_cover_letter
if will_exceed_limit(p.get("description") or "", resume_content):
    client.table("matches").update({
        "draft_status": "failed_token_limit",
        "token_estimate": estimate_tokens(p.get("description") or ""),
        "draft_attempts": match.get("draft_attempts", 0) + 1
    }).eq("id", match["id"]).execute()
    print(f"  skipped — token limit: ~{estimate_tokens(p.get('description') or '')} tokens")
    continue
        # Step 1: Draft
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

        # Step 2: Faithfulness eval
        print("\n  running faithfulness evaluation...")
        try:
            faith_result = score_faithfulness(
                draft=draft_text,
                resume_sections=resume_sections,
                job_description=p.get("description") or "",
            )
        except Exception as e:
            print(f"  faithfulness eval failed: {e}")
            faith_result = {
                "faithfulness_score": None,
                "flag": "eval error",
                "passes": True,
                "verdicts": [],
            }

        # Step 3: Quality eval
        quality_result = score_quality(draft_text)

        # Step 4: Store to Supabase
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
        }

        client.table("matches").update({
            "draft": draft_text,
            "tailored_resume": json.dumps(eval_metadata),
        }).eq("id", match["id"]).execute()

        # Print final output
        print(f"\n{'─'*55}")
        print(f"COVER LETTER — {p['title']} @ {company}")
        print(f"{'─'*55}")
        print(draft_text)
        print(f"{'─'*55}")
        print(f"Faithfulness : {faith_result.get('faithfulness_score', 'N/A')} — {faith_result.get('flag')}")
        print(f"Quality      : {quality_result.get('quality_score')} — {'PASS' if quality_result.get('passes') else 'NEEDS REVISION'}")
        if quality_result.get("banned_found"):
            print(f"Banned found : {', '.join(quality_result['banned_found'])}")

    print("\n\n── Phase 4 Done ──\n")


if __name__ == "__main__":
    run()
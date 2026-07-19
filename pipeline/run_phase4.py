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
from interview_prep import requires_cover_letter, generate_interview_prep


def estimate_tokens(text: str) -> int:
    return len(text) // 4


def will_exceed_limit(job_desc: str, resume: str) -> bool:
    total = estimate_tokens(job_desc) + estimate_tokens(resume) + 800
    return total > 5500


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
    resume_content = profile.data.get("content") or ""

    if not resume_sections:
        print("  resume sections empty — check embed.py chunking")
        return

    print(f"  loaded {len(resume_sections)} resume sections: {list(resume_sections.keys())}")

    matches = (
        client.table("matches")
        .select("id, posting_id, score, draft_attempts")
        .is_("draft", "null")
        .order("score", desc=True)
        .limit(10)
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
        job_desc = p.get("description") or ""

        print(f"\n{'═'*55}")
        print(f"  [{i}/{len(matches.data)}] {p['title']} @ {company}")
        print(f"  match score: {match['score']:.3f}")

        # ── Token limit check ──
        if will_exceed_limit(job_desc, resume_content):
            token_est = estimate_tokens(job_desc)
            print(f"  skipped — token limit risk (~{token_est} tokens in JD)")
            client.table("matches").update({
                "draft_status": "failed_token_limit",
                "token_estimate": token_est,
                "draft_attempts": (match.get("draft_attempts") or 0) + 1,
            }).eq("id", match["id"]).execute()
            continue

        print(f"{'═'*55}")

        # ── Decide: cover letter or interview prep ──
        needs_cover_letter = requires_cover_letter(job_desc)
        mode = "cover_letter" if needs_cover_letter else "interview_prep"
        print(f"\n  mode: {mode}")

        if mode == "cover_letter":
            print("\n  running drafting crew...")
            try:
                result = draft_cover_letter(
                    job_title=p["title"],
                    company=company,
                    job_description=job_desc,
                    resume_sections=resume_sections,
                )
                draft_text = result["draft"]
                print(f"  draft complete ({len(draft_text)} chars)")
            except Exception as e:
                print(f"  drafting failed: {e}")
                client.table("matches").update({
                    "draft_status": "failed_other",
                    "draft_attempts": (match.get("draft_attempts") or 0) + 1,
                }).eq("id", match["id"]).execute()
                continue

            # Evaluate
            print("\n  running faithfulness evaluation...")
            try:
                faith_result = score_faithfulness(
                    draft=draft_text,
                    resume_sections=resume_sections,
                    job_description=job_desc,
                )
            except Exception as e:
                print(f"  faithfulness eval failed: {e}")
                faith_result = {"faithfulness_score": None, "flag": "eval error", "passes": True, "verdicts": []}

            quality_result = score_quality(draft_text)

            eval_metadata = {
                "output_type": "cover_letter",
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
                "draft_status": "drafted",
                "tailored_resume": json.dumps(eval_metadata),
                "draft_attempts": (match.get("draft_attempts") or 0) + 1,
            }).eq("id", match["id"]).execute()

            print(f"\n{'─'*55}")
            print(f"COVER LETTER — {p['title']} @ {company}")
            print(f"{'─'*55}")
            print(draft_text)
            print(f"{'─'*55}")
            print(f"Faithfulness : {faith_result.get('faithfulness_score', 'N/A')} — {faith_result.get('flag')}")
            print(f"Quality      : {quality_result.get('quality_score')} — {'PASS' if quality_result.get('passes') else 'NEEDS REVISION'}")

        else:
            # ── Interview prep mode ──
            print("\n  generating interview prep...")
            try:
                prep_result = generate_interview_prep(
                    job_title=p["title"],
                    company=company,
                    job_description=job_desc,
                    resume_sections=resume_sections,
                )

                prep_json = json.dumps(prep_result)

                client.table("matches").update({
                    "draft": f"[INTERVIEW PREP]\n\n{prep_json}",
                    "draft_status": "drafted",
                    "tailored_resume": json.dumps({
                        "output_type": "interview_prep",
                        "prep": prep_result,
                    }),
                    "draft_attempts": (match.get("draft_attempts") or 0) + 1,
                }).eq("id", match["id"]).execute()

                questions = prep_result.get("questions", {})
                technical = questions.get("technical", [])
                behavioral = questions.get("behavioral", [])
                role_specific = questions.get("role_specific", [])

                print(f"\n{'─'*55}")
                print(f"INTERVIEW PREP — {p['title']} @ {company}")
                print(f"{'─'*55}")
                print(f"\nRole: {prep_result.get('focus_areas', {}).get('role_in_one_line', '')}\n")

                print("TECHNICAL QUESTIONS:")
                for q in technical:
                    print(f"\n  Q: {q.get('question')}")
                    print(f"  → {q.get('answer_from_resume')}")

                print("\nBEHAVIORAL QUESTIONS:")
                for q in behavioral:
                    print(f"\n  Q: {q.get('question')}")
                    print(f"  → {q.get('answer_from_resume')}")

                print("\nROLE-SPECIFIC QUESTIONS:")
                for q in role_specific:
                    print(f"\n  Q: {q.get('question')}")
                    print(f"  → {q.get('answer_from_resume')}")

                ask_them = questions.get("questions_to_ask_them", [])
                if ask_them:
                    print("\nASK THEM:")
                    for q in ask_them:
                        print(f"  • {q}")

                print(f"{'─'*55}")
                print(f"  interview prep stored successfully")

            except Exception as e:
                print(f"  interview prep failed: {e}")
                client.table("matches").update({
                    "draft_status": "failed_other",
                    "draft_attempts": (match.get("draft_attempts") or 0) + 1,
                }).eq("id", match["id"]).execute()

    print("\n\n── Phase 4 Done ──\n")


if __name__ == "__main__":
    run()
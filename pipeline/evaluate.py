import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")
_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    return _llm


def score_faithfulness(
    draft: str,
    resume_sections: dict,
    job_description: str,
) -> dict:
    """
    RAGAS-inspired faithfulness evaluation.

    Step 1: Extract every factual claim from the draft.
    Step 2: For each claim, check if the resume supports it.
    Step 3: Score = supported_claims / total_claims.

    A score of 1.0 means every claim in the draft is grounded in the resume.
    A score below 0.8 flags a hallucination risk.

    Returns dict with score, per-claim verdicts, and pass/fail flag.
    """
    llm = _get_llm()
    parser = StrOutputParser()

    # Flatten resume into a single reference string
    resume_text = "\n\n".join([
        f"{section.upper()}: {content}"
        for section, content in resume_sections.items()
        if content
    ])

    # ── Step 1: Extract claims ──
    claim_extraction_prompt = ChatPromptTemplate.from_template("""
You are extracting factual claims from a cover letter.

A factual claim is any statement that asserts something specific about the writer:
- Tools or technologies they used
- Projects they built
- Roles they held
- Results or metrics they achieved
- Skills they have

Extract every factual claim as a numbered list.
One claim per line. Be specific. Do not paraphrase vaguely.

Cover letter:
{draft}

Output format:
1. [claim]
2. [claim]
...
    """)

    claim_chain = claim_extraction_prompt | llm | parser
    claims_raw = claim_chain.invoke({"draft": draft})

    # Parse numbered list into individual claims
    claims = []
    for line in claims_raw.strip().split("\n"):
        line = line.strip()
        if line and line[0].isdigit() and "." in line:
            claim_text = line.split(".", 1)[1].strip()
            if claim_text:
                claims.append(claim_text)

    if not claims:
        return {
            "faithfulness_score": 1.0,
            "total_claims": 0,
            "supported_claims": 0,
            "verdicts": [],
            "passes": True,
            "flag": "no claims extracted",
        }

    # ── Step 2: Verify each claim against resume ──
    verify_prompt = ChatPromptTemplate.from_template("""
You are a strict fact-checker verifying a cover letter claim against a resume.

Resume (ground truth):
{resume_text}

Claim to verify:
{claim}

Answer with ONLY one word: SUPPORTED or UNSUPPORTED

- SUPPORTED: the resume clearly mentions this tool, project, skill, or experience
- UNSUPPORTED: the resume does not mention this, or the claim exaggerates what the resume says

One word only:
    """)

    verify_chain = verify_prompt | llm | parser

    verdicts = []
    supported = 0

    for claim in claims:
        verdict_raw = verify_chain.invoke({
            "resume_text": resume_text[:3000],
            "claim": claim,
        }).strip().upper()

        is_supported = "SUPPORTED" in verdict_raw
        if is_supported:
            supported += 1

        verdicts.append({
            "claim": claim,
            "verdict": "SUPPORTED" if is_supported else "UNSUPPORTED",
        })

    # ── Step 3: Score ──
    score = supported / len(claims) if claims else 1.0
    passes = score >= 0.8

    # Print a readable summary
    print(f"\n  faithfulness breakdown:")
    for v in verdicts:
        icon = "✓" if v["verdict"] == "SUPPORTED" else "✗"
        print(f"    {icon} {v['claim'][:80]}")
    print(f"  score: {supported}/{len(claims)} = {score:.2f} — {'PASS' if passes else 'FAIL'}\n")

    return {
        "faithfulness_score": round(score, 3),
        "total_claims": len(claims),
        "supported_claims": supported,
        "verdicts": verdicts,
        "passes": passes,
        "flag": "clean" if passes else "hallucination risk — review before sending",
    }
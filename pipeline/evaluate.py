import os
from dotenv import load_dotenv
from pathlib import Path

for _parent in [Path(__file__).parent, Path(__file__).parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

_llm = None

BANNED_PHRASES = [
    "i am comfortable", "i am interested", "natural next step",
    "strong foundation", "aligns with", "with my technical skills",
    "with my skills", "fast-paced", "collaborative team",
    "driving innovation", "delivering impact", "i am eager",
    "i believe", "leverage", "i would love", "i am passionate",
    "make me a good fit", "i am confident", "i am dedicated",
    "excited to", "thrilled to",
]


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
    llm = _get_llm()
    parser = StrOutputParser()

    resume_text = "\n\n".join([
        f"{section.upper()}: {content}"
        for section, content in resume_sections.items()
        if content
    ])

    claim_prompt = ChatPromptTemplate.from_template("""
Extract every factual claim from this cover letter as a numbered list.
A factual claim: tools used, projects built, roles held, results achieved, skills stated.
One claim per line. Be specific.

Cover letter:
{draft}

Output:
1. [claim]
2. [claim]
    """)

    claims_raw = (claim_prompt | llm | parser).invoke({"draft": draft})

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

    verify_prompt = ChatPromptTemplate.from_template("""
You are a strict fact-checker.

Resume (ground truth):
{resume_text}

Claim to verify:
{claim}

Answer with ONLY one word: SUPPORTED or UNSUPPORTED
    """)

    verify_chain = verify_prompt | llm | parser
    verdicts = []
    supported = 0

    for claim in claims:
        result = verify_chain.invoke({
            "resume_text": resume_text[:3000],
            "claim": claim,
        }).strip().upper()

        is_supported = "SUPPORTED" in result
        if is_supported:
            supported += 1

        verdicts.append({
            "claim": claim,
            "verdict": "SUPPORTED" if is_supported else "UNSUPPORTED",
        })

    score = supported / len(claims) if claims else 1.0
    passes = score >= 0.8

    print(f"\n  faithfulness breakdown:")
    for v in verdicts:
        icon = "✓" if v["verdict"] == "SUPPORTED" else "✗"
        print(f"    {icon} {v['claim'][:80]}")
    print(f"  faithfulness: {supported}/{len(claims)} = {score:.2f} — {'PASS' if passes else 'FAIL'}")

    return {
        "faithfulness_score": round(score, 3),
        "total_claims": len(claims),
        "supported_claims": supported,
        "verdicts": verdicts,
        "passes": passes,
        "flag": "clean" if passes else "hallucination risk — review before sending",
    }


def score_quality(draft: str) -> dict:
    """
    Checks for banned generic phrases.
    Each banned phrase found deducts 0.1 from the score.
    Score of 1.0 = no banned phrases found.
    """
    draft_lower = draft.lower()
    found = [phrase for phrase in BANNED_PHRASES if phrase in draft_lower]
    score = max(0.0, round(1.0 - (len(found) * 0.1), 2))

    print(f"\n  quality check:")
    if found:
        for phrase in found:
            print(f"    ✗ banned phrase found: '{phrase}'")
    else:
        print(f"    ✓ no banned phrases found")
    print(f"  quality score: {score:.2f} — {'PASS' if score >= 0.8 else 'NEEDS REVISION'}")

    return {
        "quality_score": score,
        "banned_found": found,
        "passes": score >= 0.8,
    }
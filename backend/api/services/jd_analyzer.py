import os
import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from pathlib import Path

for _parent in [Path(__file__).parent, Path(__file__).parent.parent,
                Path(__file__).parent.parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    return _llm


def _get_resume() -> str:
    """Load resume from project root."""
    for path in [
        Path(__file__).parent.parent.parent.parent / "resume.txt",
        Path(__file__).parent.parent.parent / "resume.txt",
    ]:
        if path.exists():
            return path.read_text()
    return ""


def analyze_jd(jd_text: str) -> dict:
    """
    Analyzes a pasted job description against the user's resume.
    Returns role summary, fit analysis, and interview questions.
    """
    llm = _get_llm()
    parser = StrOutputParser()
    resume = _get_resume()

    # ── Step 1: Role Summary ──
    role_prompt = ChatPromptTemplate.from_template("""
Analyze this job description and extract the following in JSON format:
{{
    "actual_role": "one sentence describing what this person will actually do day to day",
    "seniority": "junior/mid/senior/lead",
    "key_requirements": ["top 5 actual requirements, not buzzwords"],
    "nice_to_have": ["genuine nice-to-haves"],
    "red_flags": ["anything suspicious or concerning about the role"],
    "company_type": "startup/scaleup/enterprise/agency/consultancy",
    "remote": true/false
}}

Return ONLY the JSON. No preamble.

Job description:
{jd_text}
    """)

    role_raw = (role_prompt | llm | parser).invoke({"jd_text": jd_text[:3000]})
    try:
        clean = role_raw.strip().replace("```json", "").replace("```", "")
        role_data = json.loads(clean)
    except Exception:
        role_data = {"actual_role": role_raw, "error": "parse failed"}

    # ── Step 2: CV Fit Map ──
    fit_prompt = ChatPromptTemplate.from_template("""
You are mapping a candidate's resume to a job description.

For each key requirement in the JD, find the specific resume evidence that addresses it.
Be honest about gaps — if nothing in the resume addresses a requirement, say so clearly.

Return JSON:
{{
    "strong_matches": [
        {{
            "requirement": "what JD asks for",
            "evidence": "specific resume bullet or project that proves it",
            "strength": "strong/moderate/weak"
        }}
    ],
    "gaps": [
        {{
            "requirement": "what JD asks for",
            "gap": "honest description of what's missing",
            "mitigation": "how to address this in the cover letter or interview"
        }}
    ],
    "overall_fit": "strong/moderate/weak",
    "fit_summary": "2 sentences: honest assessment of how well this candidate fits"
}}

Return ONLY the JSON.

Resume:
{resume}

Job description:
{jd_text}
    """)

    fit_raw = (fit_prompt | llm | parser).invoke({
        "resume": resume[:2000],
        "jd_text": jd_text[:2000],
    })
    try:
        clean = fit_raw.strip().replace("```json", "").replace("```", "")
        fit_data = json.loads(clean)
    except Exception:
        fit_data = {"fit_summary": fit_raw, "error": "parse failed"}

    # ── Step 3: Interview Questions ──
    questions_prompt = ChatPromptTemplate.from_template("""
Generate interview preparation questions for this role.

Return JSON with three categories:
{{
    "technical": [
        {{
            "question": "the question",
            "why_asked": "what they're actually testing",
            "your_answer_hint": "which part of your resume/experience to draw from"
        }}
    ],
    "behavioral": [
        {{
            "question": "the question",
            "why_asked": "what they're actually testing",
            "your_answer_hint": "which experience to reference"
        }}
    ],
    "role_specific": [
        {{
            "question": "the question",
            "why_asked": "what they're actually testing",
            "your_answer_hint": "how to answer based on the resume"
        }}
    ]
}}

Generate 4 questions per category. Return ONLY the JSON.

Resume summary:
{resume}

Job description:
{jd_text}
    """)

    questions_raw = (questions_prompt | llm | parser).invoke({
        "resume": resume[:1500],
        "jd_text": jd_text[:2000],
    })
    try:
        clean = questions_raw.strip().replace("```json", "").replace("```", "")
        questions_data = json.loads(clean)
    except Exception:
        questions_data = {"error": "parse failed", "raw": questions_raw}

    return {
        "role_summary": role_data,
        "fit_analysis": fit_data,
        "interview_questions": questions_data,
    }
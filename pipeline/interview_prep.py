import os
import json
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


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    return _llm


def requires_cover_letter(job_description: str) -> bool:
    """
    Scans JD text for explicit cover letter request signals.
    Returns True only if the JD explicitly asks for one.
    Default is False — most postings don't ask.
    """
    indicators = [
        "cover letter",
        "covering letter",
        "application letter",
        "motivation letter",
        "letter of motivation",
        "write to us",
        "tell us why you",
        "please include a letter",
        "submit a letter",
        "attach a letter",
    ]
    jd_lower = job_description.lower()
    return any(indicator in jd_lower for indicator in indicators)


def generate_interview_prep(
    job_title: str,
    company: str,
    job_description: str,
    resume_sections: dict,
) -> dict:
    """
    2-call interview prep pipeline. Lightweight alternative to the
    3-agent cover letter crew when no cover letter is requested.

    Call 1: Extract what this role actually needs and what they
            will test for in interviews.
    Call 2: Generate grounded Q&A using the resume as the answer source.

    Returns a structured dict with technical, behavioral, and
    role-specific questions each with a grounded answer hint.
    """
    llm = _get_llm()
    parser = StrOutputParser()

    resume_context = "\n\n".join([
        f"{section.upper()}:\n{content}"
        for section, content in resume_sections.items()
        if content and len(content.strip()) > 10
    ])

    # ── Call 1: Extract interview focus areas ──
    extract_prompt = ChatPromptTemplate.from_template("""
You are preparing a candidate for a job interview.

Analyze this job description and extract what interviewers will actually test for.
Return JSON only — no preamble, no markdown fences.

{{
    "role_in_one_line": "what this person will actually do day to day",
    "must_know_technical": ["top 4 technical areas they will definitely test"],
    "likely_scenarios": ["top 3 behavioral situations they will probe"],
    "culture_signals": ["2 things about how this team works based on the JD"],
    "likely_red_flags_for_candidate": ["what gaps in your background they might push on"]
}}

Job title: {job_title}
Company: {company}
Job description: {job_description}
    """)

    extract_raw = (extract_prompt | llm | parser).invoke({
        "job_title": job_title,
        "company": company,
        "job_description": job_description[:2500],
    })

    try:
        clean = extract_raw.strip().replace("```json", "").replace("```", "")
        focus_areas = json.loads(clean)
    except Exception:
        focus_areas = {"role_in_one_line": extract_raw}

    # ── Call 2: Generate grounded Q&A ──
    qa_prompt = ChatPromptTemplate.from_template("""
Generate interview questions and grounded answers for this candidate.

STRICT RULE: Every answer hint must reference something specific from the
candidate's resume. If the resume does not address a question, say so honestly
and suggest how to bridge the gap. Do not invent experience.

Return JSON only — no preamble, no markdown fences.

{{
    "technical": [
        {{
            "question": "specific technical question they will ask",
            "what_they_test": "the real thing they want to know",
            "answer_from_resume": "which project or experience to reference and what to say"
        }}
    ],
    "behavioral": [
        {{
            "question": "behavioral question using situation/task/action/result format",
            "what_they_test": "the real thing they want to know",
            "answer_from_resume": "which experience maps to this and what the result was"
        }}
    ],
    "role_specific": [
        {{
            "question": "question specific to this exact role and company",
            "what_they_test": "the real thing they want to know",
            "answer_from_resume": "how to answer this from your actual background"
        }}
    ],
    "questions_to_ask_them": [
        "smart question you should ask the interviewer that shows you understand the role"
    ]
}}

Generate 5 technical questions, 4 behavioral questions, 3 role-specific questions,
and 3 questions to ask them.

Role focus areas: {focus_areas}

Candidate resume:
{resume_context}

Job description:
{job_description}
    """)

    qa_raw = (qa_prompt | llm | parser).invoke({
        "focus_areas": json.dumps(focus_areas, indent=2),
        "resume_context": resume_context[:2000],
        "job_description": job_description[:1500],
    })

    try:
        clean = qa_raw.strip().replace("```json", "").replace("```", "")
        qa_data = json.loads(clean)
    except Exception:
        qa_data = {"raw": qa_raw, "parse_error": True}

    return {
        "output_type": "interview_prep",
        "focus_areas": focus_areas,
        "questions": qa_data,
        "job_title": job_title,
        "company": company,
    }
import os
from dotenv import load_dotenv
from pathlib import Path

for _parent in [Path(__file__).parent, Path(__file__).parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import TavilySearchTool
import crewai.llms.cache as _crewai_cache
_crewai_cache.mark_cache_breakpoint = lambda msg: msg

def _get_llm():
    return LLM(
        model="groq/llama-3.3-70b-versatile",
        temperature=0.3,
    )


def _get_search_tool():
    # TavilySearchTool reads TAVILY_API_KEY from environment automatically
    return TavilySearchTool()


def draft_cover_letter(
    job_title: str,
    company: str,
    job_description: str,
    resume_sections: dict,
) -> dict:
    llm = _get_llm()
    search = _get_search_tool()

    resume_context = "\n\n".join([
        f"=== {section.upper()} ===\n{content}"
        for section, content in resume_sections.items()
        if content and len(content.strip()) > 10
    ])

    researcher = Agent(
        role="Company Intelligence Specialist",
        goal=(
            "Find one or two specific, recent things about this company "
            "that would make a cover letter feel genuinely informed."
        ),
        backstory=(
            "You research companies for job applicants. You skip generic descriptions "
            "and find what makes this specific company distinct right now."
        ),
        tools=[search],
        llm=llm,
        verbose=True,
        max_iter=3,
    )

    drafter = Agent(
        role="Technical Cover Letter Writer",
        goal=(
            "Write a cover letter grounded entirely in the candidate's resume. "
            "Never invent or exaggerate. Every claim must trace back to a real "
            "bullet point or project in the resume sections provided."
        ),
        backstory=(
            "You write cover letters for AI engineers applying to technical roles. "
            "Your strict rule: if the resume does not say it, you do not say it. "
            "No em dashes. No I am passionate about. No excited to apply. "
            "Direct, specific, varied sentence lengths."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    refiner = Agent(
        role="Human-Voice Editor",
        goal="Make the cover letter sound like a real person wrote it.",
        backstory=(
            "You edit cover letters to remove AI-detectable patterns. "
            "You cut em dashes, passionate, excited, I would love to, "
            "I believe, I am eager, leverage, utilize, and anything templated. "
            "You keep every specific fact and project reference intact. "
            "Output only the final letter with no preamble and no commentary."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    research_task = Task(
        description=f"""
Research the company '{company}' for the role '{job_title}'.

Find:
1. What the company actually does in one specific sentence
2. One recent specific thing: a product launch, funding round, or tech decision
3. What kind of engineer would genuinely fit here based on the JD

Job description excerpt:
{job_description[:800]}
        """,
        expected_output=(
            "3 to 4 sentences of specific, recent company intelligence. "
            "No generic language."
        ),
        agent=researcher,
    )

    draft_task = Task(
        description=f"""
Write a cover letter for this application.

STRICT CONSTRAINT: Every factual claim must come directly from the
resume sections below. Do not invent tools, projects, or experience.

Job title: {job_title}
Company: {company}

Job description:
{job_description[:1500]}

Resume sections:
{resume_context[:2000]}

Structure:
- Paragraph 1: Why this company specifically, using the research
- Paragraph 2: What you have built that is directly relevant, resume only
- Paragraph 3: What you want to do here and why it is a natural next step

No subject line. No greeting. Just the three paragraphs.
        """,
        expected_output="A 3-paragraph cover letter grounded in the resume.",
        agent=drafter,
        context=[research_task],
    )

    refine_task = Task(
        description="""
Refine the cover letter from the previous task.

Remove: em dashes, passionate, excited, I would love to, I believe,
I am eager, leverage, utilize, and any templated phrases.

Keep all project names, tool names, numbers, and results.
Keep the three-paragraph structure.
Output ONLY the final letter. Nothing before or after it.
        """,
        expected_output="Final cover letter text only.",
        agent=refiner,
        context=[draft_task],
    )

    crew = Crew(
        agents=[researcher, drafter, refiner],
        tasks=[research_task, draft_task, refine_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    research_notes = ""
    if hasattr(research_task, "output") and research_task.output:
        research_notes = research_task.output.raw

    return {
        "draft": str(result),
        "company_research": research_notes,
    }
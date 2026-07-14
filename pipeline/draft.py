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

def _get_llm():
    return LLM(
        model="openai/llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
        temperature=0.3,
    )

def _get_search_tool():
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
            "Find specific, concrete details about what this company builds "
            "and what their engineering culture looks like."
        ),
        backstory=(
            "You research companies for job applicants. "
            "You completely ignore acquisitions, funding rounds, and financial news. "
            "You focus only on what the company actually builds, their tech stack, "
            "their engineering problems, and what kind of work happens day to day. "
            "You find one specific technical or product detail that makes the "
            "company interesting to an engineer."
        ),
        tools=[search],
        llm=llm,
        verbose=True,
        max_iter=3,
    )

    drafter = Agent(
        role="Technical Cover Letter Writer",
        goal=(
            "Write a cover letter that sounds like a confident engineer "
            "wrote it, not a job applicant. "
            "Every claim must trace back to the resume sections provided. "
            "Never invent tools, projects, or experience."
        ),
        backstory=(
            "You write cover letters for AI engineers. "
            "Your rules: if the resume does not say it, you do not say it. "
            "You never use: em dashes, passionate, excited, I would love to, "
            "I believe, I am eager, leverage, utilize, aligns with, "
            "fast-paced, collaborative team, strong foundation, "
            "natural next step, driving innovation, delivering impact, "
            "I am comfortable, I am interested in, with my skills. "
            "You write like a person who knows what they built and why it matters. "
            "Short sentences. Specific details. No fluff."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    refiner = Agent(
        role="Human-Voice Editor",
        goal=(
            "Strip every generic corporate phrase from the letter "
            "and make it sound like a real engineer wrote it."
        ),
        backstory=(
            "You edit cover letters with zero tolerance for AI-sounding language. "
            "You remove: em dashes, passionate, excited, I would love to, "
            "I believe, I am eager, leverage, utilize, aligns with, "
            "fast-paced, collaborative team, strong foundation, "
            "natural next step, driving innovation, delivering impact, "
            "I am comfortable, I am interested in, with my skills, "
            "make me a good fit, I am confident, I am dedicated. "
            "When you find a banned phrase you rewrite that sentence from scratch. "
            "You keep every project name, tool name, and number exactly as written. "
            "Output only the final letter. No preamble. No commentary. "
            "No 'Here is the refined cover letter' before the text."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    research_task = Task(
        description=f"""
Research the company '{company}' for the role '{job_title}'.

IGNORE completely: acquisitions, mergers, funding rounds, stock prices,
financial transactions, and investment activity. These are useless for
a cover letter.

FIND instead:
1. What this company actually builds or ships — one specific sentence
2. One technical or product detail that an engineer would find genuinely
   interesting — a specific tool, architecture decision, product feature,
   or engineering problem they are solving
3. What kind of engineer thrives here based on the JD

Job description excerpt:
{job_description[:800]}
        """,
        expected_output=(
            "3 sentences maximum. Specific technical or product detail. "
            "No financial news. No generic company descriptions."
        ),
        agent=researcher,
    )

    draft_task = Task(
        description=f"""
Write a cover letter for this application.

STRICT CONSTRAINT: Every factual claim must come directly from the
resume sections below. Do not invent anything.

BANNED PHRASES — never use these:
- passionate, excited, I would love to, I believe, I am eager
- leverage, utilize, aligns with, fast-paced, collaborative team
- strong foundation, natural next step, driving innovation
- delivering impact, I am comfortable, I am interested in
- with my skills, make me a good fit, I am confident

Job title: {job_title}
Company: {company}

Job description:
{job_description[:1500]}

Resume sections — only facts from here may appear:
{resume_context[:2000]}

Use the company research from the previous task for the opening.

Structure — three paragraphs, no greeting, no subject line:

Paragraph 1: One specific thing about what this company builds or the
problem they are solving. One sentence connecting that to something
you have actually built. Keep it under 4 sentences total.

Paragraph 2: Two or three specific things you have built that are
directly relevant. Name the project. Name the tool. State what it did.
No adjectives unless they come from the resume.

Paragraph 3: What you want to work on here specifically. Not generic
enthusiasm. A specific technical problem or product direction from the JD
that connects to something real in your background.
        """,
        expected_output=(
            "Three paragraphs. No greeting. No banned phrases. "
            "Every claim traceable to the resume."
        ),
        agent=drafter,
        context=[research_task],
    )

    refine_task = Task(
        description="""
Read the cover letter from the previous task carefully.

For every sentence that contains a banned phrase, rewrite the entire
sentence from scratch without the phrase. Do not just delete the phrase
and leave a broken sentence.

Banned phrases to eliminate:
passionate, excited, I would love to, I believe, I am eager,
leverage, utilize, aligns with, fast-paced, collaborative team,
strong foundation, natural next step, driving innovation,
delivering impact, I am comfortable, I am interested in,
with my skills, make me a good fit, I am confident, I am dedicated,
em dashes.

After removing banned phrases, read the whole letter again and ask:
does this sound like a real engineer or like a cover letter template?
If it still sounds templated, rewrite those sentences.

Output ONLY the final letter text.
No "Here is the refined version." No preamble. No commentary.
Start directly with the first paragraph.
        """,
        expected_output=(
            "Final cover letter only. "
            "Starts directly with paragraph text, no preamble."
        ),
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
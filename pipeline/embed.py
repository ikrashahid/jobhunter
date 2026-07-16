import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from supabase import create_client

# BGE small is the sweet spot — better than MiniLM, faster than large
# runs fully locally, no API key, no cost
MODEL_NAME = "BAAI/bge-small-en-v1.5"

_model = None
_client = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print("  loading BGE model (first time only)...")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_client():
    global _client
    if _client is None:
        _client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    return _client


def embed_text(text: str) -> list[float]:
    """
    Embeds a single string using BGE.
    BGE performs better with this prefix for retrieval tasks.
    """
    model = get_model()
    prefixed = f"Represent this sentence for retrieval: {text}"
    vector = model.encode(prefixed, normalize_embeddings=True)
    return vector.tolist()


def embed_resume(resume_text: str, label: str = "main") -> str:
    """
    Embeds your resume and upserts it into the profile table.
    Call this once when you update your resume.
    Returns the profile id.
    """
    client = get_client()
    vector = embed_text(resume_text)

    # sections is a dict of labelled resume chunks for the drafting agents
    sections = _chunk_resume(resume_text)

    response = (
        client.table("profile")
        .upsert(
            {
                "label": label,
                "content": resume_text,
                "sections": sections,
                "embedding": vector,
            },
            on_conflict="label",
        )
        .execute()
    )
    print(f"  resume embedded and stored ({len(vector)}-dim vector)")
    return response.data[0]["id"]


def embed_unembedded_postings(batch_size: int = 50) -> int:
    """
    Finds all postings with no embedding yet and embeds them.
    Runs in batches to avoid memory issues.
    Returns count of postings embedded.
    """
    client = get_client()

    # Fetch postings that have no embedding yet
    response = (
        client.table("postings")
        .select("id, title, description")
        .is_("embedding", "null")
        .limit(batch_size)
        .execute()
    )
    postings = response.data

    if not postings:
        print("  no unembedded postings found")
        return 0

    print(f"  embedding {len(postings)} postings...")

    embedded = 0
    for posting in postings:
        description = posting.get("description", "") or ""
        word_count = len(description.split())

        # Combine title + description for richer embedding
        # Title gets repeated for emphasis — a trick that improves retrieval
        text = f"{posting['title']} {posting['title']} {description}"
        text = text[:2000]  # cap to avoid very long descriptions

        vector = embed_text(text)

        client.table("postings").update(
            {"embedding": vector, "description_word_count": word_count}
        ).eq("id", posting["id"]).execute()

        if word_count < 60:
            print(f"    [thin description] '{posting['title']}' — only {word_count} words")

        embedded += 1

    print(f"  embedded {embedded} postings")
    return embedded


def _chunk_resume(text: str) -> dict:
    """
    Splits resume into named sections for targeted retrieval.
    Simple heuristic: looks for common section headers.
    """
    sections = {}
    current_section = "general"
    current_lines = []

    headers = [
        "experience", "education", "skills", "projects",
        "certifications", "summary", "objective", "work history"
    ]

    for line in text.split("\n"):
        lower = line.lower().strip()
        matched = next((h for h in headers if lower.startswith(h)), None)
        if matched and len(line.strip()) < 40:
            if current_lines:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = matched
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections
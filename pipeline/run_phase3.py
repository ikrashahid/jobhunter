from dotenv import load_dotenv
load_dotenv()

import os
from embed import embed_resume, embed_unembedded_postings
from score import score_postings
from supabase import create_client


def run():
    print("\n── Phase 3: Embed + Score ──\n")

    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # --- Step 1: Embed your resume ---
    # Paste your actual resume text here as a plain string
    # or load from a file
    resume_path = os.path.join(os.path.dirname(__file__), "../resume.txt")
    if os.path.exists(resume_path):
        with open(resume_path, "r") as f:
            resume_text = f.read()
    else:
        print("  resume.txt not found — create it at the project root")
        return

    print("Embedding resume...")
    embed_resume(resume_text, label="main")

    # --- Step 2: Embed all unembedded postings ---
    print("\nEmbedding postings...")
    embed_unembedded_postings(batch_size=50)

    # --- Step 3: Score postings against resume ---
    print("\nScoring postings...")
    profile = client.table("profile").select("embedding, content").eq("label", "main").single().execute()
    resume_embedding = profile.data["embedding"]
    resume_content = profile.data["content"]

    matches = score_postings(resume_content, resume_embedding)

    print(f"\nTop matches:")
    for m in matches[:5]:
        print(f"  [{m['final_score']:.2f}] {m.get('title')} — {m.get('company')}")

    print("\n── Done ──\n")


if __name__ == "__main__":
    run()
import os
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from supabase import create_client

SCORE_THRESHOLD = 0.45   # kept for reference / future recalibration once scores are healthy
TOP_K_RETRIEVE = 20      # how many candidates go into re-ranking
TOP_K_RERANK = 5         # final shortlist after re-ranking

# The cross-encoder (ms-marco-MiniLM-L-6-v2) was trained on short queries
# paired with a single passage, with a combined 512-TOKEN budget for both
# sides together. Feeding it a full resume + full job description blows
# past that budget, gets silently truncated by the tokenizer, and pushes
# the model into a narrow, meaningless score range. Keep both sides short.
CROSS_ENCODER_RESUME_CHARS = 500
CROSS_ENCODER_JOB_CHARS = 500

_cross_encoder = None
_client = None


def get_cross_encoder() -> CrossEncoder:
    global _cross_encoder
    if _cross_encoder is None:
        print("  loading cross-encoder...")
        _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _cross_encoder


def get_client():
    global _client
    if _client is None:
        _client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY")
        )
    return _client


def score_postings(resume_text: str, resume_embedding: list[float]) -> list[dict]:
    """
    Full hybrid scoring pipeline:
    1. pgvector retrieves top candidates by cosine similarity
    2. BM25 scores the same candidates by keyword overlap
    3. RRF combines both rankings
    4. Cross-encoder re-ranks the top K
    5. Top N results stored in matches table

    Returns list of scored matches.
    """
    client = get_client()

    # --- Step 1: Vector retrieval via pgvector ---
    # Uses the match_postings RPC we'll create in Supabase
    vector_results = _vector_retrieve(resume_embedding, TOP_K_RETRIEVE * 2)

    if not vector_results:
        print("  no postings to score")
        return []

    # --- Step 2: BM25 keyword scoring ---
    bm25_scores = _bm25_score(resume_text, vector_results)

    # --- Step 3: Reciprocal Rank Fusion ---
    combined = _rrf_combine(vector_results, bm25_scores)

    # Take top K into re-ranking
    top_candidates = combined[:TOP_K_RETRIEVE]

    # --- Step 4: Cross-encoder re-ranking ---
    reranked = _cross_encoder_rerank(resume_text, top_candidates)

    # --- DEBUG: inspect raw score distribution ---
    # Remove this block once SCORE_THRESHOLD has been recalibrated against
    # real numbers and you trust the pipeline again.
    print("\n  DEBUG — top 10 raw scores:")
    for r in reranked[:10]:
        print(f"    final={r['final_score']:.3f}  cross_raw={r['cross_score']:.3f}  title={r.get('title')!r}")
    print(f"  DEBUG — resume_text length: {len(resume_text)} chars")
    if reranked:
        sample = reranked[0]
        print(f"  DEBUG — sample posting desc length: {len(sample.get('description') or '')} chars")
        print(f"  DEBUG — sample posting desc preview: {(sample.get('description') or '')[:200]!r}\n")

    # --- Step 5: Take top N and store ---
    # Using a fixed top-N instead of an absolute SCORE_THRESHOLD for now,
    # since the cross-encoder's raw logit scale needs to be recalibrated
    # against real score distributions before an absolute cutoff is trustworthy.
    qualified = reranked[:TOP_K_RERANK]
    stored = _store_matches(qualified)

    print(f"  scored {len(combined)} postings → top {len(qualified)} selected → {stored} stored")
    return qualified


def _vector_retrieve(resume_embedding: list[float], limit: int) -> list[dict]:
    """
    Calls pgvector cosine similarity search via Supabase RPC.
    Returns postings ordered by vector similarity.
    """
    client = get_client()
    response = client.rpc(
        "match_postings",
        {
            "query_embedding": resume_embedding,
            "match_count": limit,
        }
    ).execute()
    return response.data or []


def _bm25_score(resume_text: str, postings: list[dict]) -> dict[str, float]:
    """
    Scores each posting against the resume using BM25 keyword matching.
    Returns a dict of posting_id → BM25 score.
    """
    resume_tokens = resume_text.lower().split()

    corpus = []
    ids = []
    for p in postings:
        text = f"{p.get('title', '')} {p.get('description', '')}".lower()
        corpus.append(text.split())
        ids.append(p["id"])

    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(resume_tokens)

    return {ids[i]: float(scores[i]) for i in range(len(ids))}


def _rrf_combine(
    vector_results: list[dict],
    bm25_scores: dict[str, float],
    k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion combines vector rank and BM25 rank.
    RRF score = 1/(k + rank_vector) + 1/(k + rank_bm25)
    Higher = better combined signal.
    """
    # Vector rank
    vector_rank = {r["id"]: i + 1 for i, r in enumerate(vector_results)}

    # BM25 rank (sort by score descending)
    bm25_ranked = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
    bm25_rank = {id_: i + 1 for i, (id_, _) in enumerate(bm25_ranked)}

    results = []
    for posting in vector_results:
        pid = posting["id"]
        vr = vector_rank.get(pid, len(vector_results))
        br = bm25_rank.get(pid, len(vector_results))
        rrf = 1 / (k + vr) + 1 / (k + br)
        results.append({**posting, "rrf_score": rrf})

    return sorted(results, key=lambda x: x["rrf_score"], reverse=True)


def _cross_encoder_rerank(resume_text: str, candidates: list[dict]) -> list[dict]:
    """
    Cross-encoder reads resume + JD together as a pair.
    Much more accurate than embedding similarity alone.
    Only runs on the shortlist to keep it fast.

    Both sides are truncated to short, comparable snippets -- the model's
    512-token budget covers BOTH sides of the pair combined, and it was
    trained on short query/passage pairs, not full documents.
    """
    model = get_cross_encoder()

    resume_snippet = resume_text[:CROSS_ENCODER_RESUME_CHARS]

    pairs = [
        [
            resume_snippet,
            f"{c.get('title', '')} {c.get('description', '')}"[:CROSS_ENCODER_JOB_CHARS],
        ]
        for c in candidates
    ]

    scores = model.predict(pairs)

    for i, candidate in enumerate(candidates):
        candidate["cross_score"] = float(scores[i])
        # Normalize cross-encoder score to 0-1 range using sigmoid
        candidate["final_score"] = float(1 / (1 + np.exp(-scores[i])))

    return sorted(candidates, key=lambda x: x["final_score"], reverse=True)


def _store_matches(qualified: list[dict]) -> int:
    """
    Stores qualified matches in the matches table.
    Skips if match already exists for this posting.
    """
    client = get_client()
    stored = 0

    for match in qualified:
        try:
            client.table("matches").upsert(
                {
                    "posting_id": match["id"],
                    "score": match["final_score"],
                    "notified": False,
                },
                on_conflict="posting_id",
                ignore_duplicates=True,
            ).execute()
            stored += 1
        except Exception as e:
            print(f"  match store error {match['id']}: {e}")

    return stored
import os
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder
from supabase import create_client

TOP_K_RETRIEVE = 20      # candidates entering re-ranking
TOP_K_RERANK = 10         # final shortlist stored to 10 
THIN_DESCRIPTION_WORDS = 60  # below this, embedding quality is unreliable

# The cross-encoder (ms-marco-MiniLM-L-6-v2) has a 512-token budget
# covering BOTH sides of the pair combined. Truncate hard so the model
# isn't silently cutting content and producing garbage scores.
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
    4. Cross-encoder re-ranks the shortlist
    5. Top N stored in matches table
    """
    client = get_client()

    # Step 1: vector retrieval
    vector_results = _vector_retrieve(resume_embedding, TOP_K_RETRIEVE * 2)
    if not vector_results:
        print("  no postings to score")
        return []

    # Step 2: BM25 keyword scoring
    bm25_scores = _bm25_score(resume_text, vector_results)

    # Step 3: Reciprocal Rank Fusion
    combined = _rrf_combine(vector_results, bm25_scores)

    # Step 4: Cross-encoder re-ranking on top K
    top_candidates = combined[:TOP_K_RETRIEVE]
    reranked = _cross_encoder_rerank(resume_text, top_candidates)

    # Step 5: Store top N
    qualified = reranked[:TOP_K_RERANK]
    stored = _store_matches(qualified)

    # Step 6: Log every considered posting — this is what powers the
    # dashboard's "why didn't this match" panel. Without this, a low
    # score is a dead end with no explanation.
    _log_considered_postings(
        combined=combined,
        reranked=reranked,
        qualified_ids={q["id"] for q in qualified},
    )

    print(f"  scored {len(combined)} postings → top {len(qualified)} selected → {stored} stored")
    return qualified


def _vector_retrieve(resume_embedding: list[float], limit: int) -> list[dict]:
    """
    Cosine similarity search via pgvector RPC.
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
    BM25 keyword scoring of each posting against the resume.
    Returns posting_id → score.
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
    Reciprocal Rank Fusion.
    RRF score = 1/(k + rank_vector) + 1/(k + rank_bm25)
    Combines semantic and keyword rankings into one ordered list.
    """
    vector_rank = {r["id"]: i + 1 for i, r in enumerate(vector_results)}

    bm25_ranked = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
    bm25_rank = {id_: i + 1 for i, (id_, _) in enumerate(bm25_ranked)}

    results = []
    for posting in vector_results:
        pid = posting["id"]
        vr = vector_rank.get(pid, len(vector_results))
        br = bm25_rank.get(pid, len(vector_results))
        rrf = 1 / (k + vr) + 1 / (k + br)
        results.append({**posting, "rrf_score": rrf, "vector_rank": vr, "bm25_rank": br})

    return sorted(results, key=lambda x: x["rrf_score"], reverse=True)


def _cross_encoder_rerank(resume_text: str, candidates: list[dict]) -> list[dict]:
    """
    Cross-encoder re-ranking on the shortlist.

    Reads resume snippet + job description together as a pair —
    much more accurate than embedding similarity because it sees
    both sides simultaneously before scoring.

    Min-max normalization converts raw logits to a 0-1 range
    that actually means something. Best match in the batch → 1.0,
    worst → 0.0, everything else scales between them.

    Note: sigmoid was intentionally removed. The model outputs deeply
    negative logits for resume/JD pairs (it was trained on short
    query/passage pairs), so sigmoid produced scores near 0.0001
    for everything — meaningless for ranking.
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

    raw_scores = model.predict(pairs)

    # Min-max normalization
    min_s = float(min(raw_scores))
    max_s = float(max(raw_scores))
    score_range = max_s - min_s

    print(f"\n  cross-encoder raw range: {min_s:.3f} to {max_s:.3f}")

    for i, candidate in enumerate(candidates):
        raw = float(raw_scores[i])
        candidate["cross_score"] = raw
        if score_range > 0:
            candidate["final_score"] = (raw - min_s) / score_range
        else:
            # All scores identical — postings are very similar to each other
            candidate["final_score"] = 1.0

    reranked = sorted(candidates, key=lambda x: x["final_score"], reverse=True)

    print("  top 5 after reranking:")
    for r in reranked[:5]:
        print(f"    {r['final_score']:.3f}  {r.get('title')!r}")

    return reranked


def _log_considered_postings(
    combined: list[dict],
    reranked: list[dict],
    qualified_ids: set,
) -> None:
    """
    Writes a row to match_log for every posting that was considered this
    run, with a reason if it wasn't selected. This is what lets the
    dashboard answer "why didn't this match?" instead of just showing
    a bare score.

    Reason categories, in the order they're checked:
      - thin_description   : description too short to embed meaningfully,
                              regardless of where it ranked
      - rrf_ranked_below_top20 : never reached the cross-encoder at all —
                              vector + keyword ranking wasn't strong enough
      - cross_encoder_ranked_below_top5 : reached re-ranking but didn't
                              make the final cut
      - selected            : made it into matches
    """
    client = get_client()
    reranked_ids = {r["id"] for r in reranked}
    reranked_by_id = {r["id"]: r for r in reranked}

    rows = []
    for posting in combined:
        pid = posting["id"]
        description = posting.get("description", "") or ""
        word_count = len(description.split())
        is_thin = word_count < THIN_DESCRIPTION_WORDS

        if pid in qualified_ids:
            reason = "selected"
        elif is_thin:
            reason = "thin_description"
        elif pid in reranked_ids:
            reason = "cross_encoder_ranked_below_top5"
        else:
            reason = "rrf_ranked_below_top20"

        r = reranked_by_id.get(pid, {})
        rows.append({
            "posting_id": pid,
            "vector_rank": posting.get("vector_rank"),
            "bm25_rank": posting.get("bm25_rank"),
            "rrf_score": posting.get("rrf_score"),
            "cross_encoder_score": r.get("cross_score"),
            "final_score": r.get("final_score"),
            "selected": pid in qualified_ids,
            "reason": reason,
            "description_word_count": word_count,
        })

    try:
        client.table("match_log").insert(rows).execute()
    except Exception as e:
        print(f"  match_log write failed (non-fatal): {e}")


def _store_matches(qualified: list[dict]) -> int:
    """
    Upserts qualified matches into the matches table.
    On conflict (same posting_id) does nothing — existing match preserved.
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
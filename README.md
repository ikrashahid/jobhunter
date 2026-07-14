# Job + Gig Copilot

Personal automation pipeline that scrapes job listings and freelance gigs,
scores them against a resume using hybrid vector + keyword search, and
(eventually) drafts tailored application materials — so you only spend time
on postings worth applying to.

**Status:** Phase 1–3 complete and working. Phase 4 planned.
---

## How it works

```
Job boards (Adzuna, Himalayas)
        ↓
   scraped postings → Supabase (postings table)
        ↓
   resume.txt → embedded → Supabase (profile table)
        ↓
   pgvector similarity + BM25 keyword search
        ↓
   Reciprocal Rank Fusion → top 20 candidates
        ↓
   cross-encoder re-ranking → top 5
        ↓
   stored in matches table
        ↓
   [Phase 4] CrewAI drafts cover letter → RAGAS faithfulness check → you
```

## Stack

| Layer | Tool |
|---|---|
| Database | Supabase (Postgres + pgvector) |
| Job sources | Adzuna API, Himalayas API |
| Embeddings | `BAAI/bge-small-en-v1.5` (local, `sentence-transformers`) |
| Keyword scoring | `rank-bm25` |
| Re-ranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Nightly cleanup | n8n (dedup + TTL expiry, runs 3am) |
| Drafting (Phase 4) | CrewAI |
| Eval (Phase 4) | RAGAS (faithfulness scoring) |

## Repo structure

```
jobhunter/
├── resume.txt              # plain-text resume, chunked automatically by embed.py
├── pipeline/
│   ├── embed.py             # embeds resume + postings via BGE
│   ├── score.py             # hybrid scoring: vector + BM25 + cross-encoder
│   └── run_phase3.py        # orchestrates embed → score → store
└── fetchers/                # Adzuna + Himalayas scrapers (Phase 2)
```

## Setup

1. Create a `.env` file with:
   ```
   SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
   SUPABASE_KEY=your_supabase_anon_key
   ```
2. Activate the `job` conda environment.
3. Make sure these Supabase tables exist with **unique constraints** (required for upserts):
   ```sql
   ALTER TABLE profile ADD CONSTRAINT profile_label_unique UNIQUE (label);
   ALTER TABLE matches ADD CONSTRAINT matches_posting_id_unique UNIQUE (posting_id);
   ```
4. Run the pipeline:
   ```bash
   python run_phase3.py
   ```

## Progress

- **Phase 1** — Supabase schema deployed (`postings`, `profile`, `matches`, `applications`). ✅
- **Phase 2** — Adzuna + Himalayas fetchers live; Upwork RSS and other sources dropped (broken/off-topic feeds). ✅
- **Phase 3** — Resume + postings embedded, hybrid scoring (vector + BM25 + cross-encoder) working, top 5 matches stored per run. ✅ See `PHASE3_NOTES.md` for the full debugging log.
- **Phase 4** — CrewAI drafting crew (Drafter → Refiner, sequential) + RAGAS faithfulness gate before a draft reaches the user. 🔜 Planned.

## Known limitations

- Cross-encoder raw scores are always deeply negative (model trained on
  search-query/passage pairs, not resume/job pairs) — ranking is trustworthy,
  the raw number isn't. Top-5 selection is used instead of an absolute
  score threshold.
- Top-5 has no minimum quality floor — if no postings are genuinely good
  matches, the 5 least-bad ones still get stored.

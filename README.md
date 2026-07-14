# Job + Gig Copilot

Personal automation pipeline that scrapes job listings and freelance gigs,
scores them against a resume using hybrid vector + keyword search, drafts
tailored cover letters, and automatically fact-checks its own drafts —
so you only spend time reviewing and sending applications worth sending.

**Status:** Phase 1–4 complete and working. Frontend (Phase 5) in progress.

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
   CrewAI drafting crew (Researcher → Drafter → Refiner)
        ↓
   faithfulness check (claim extraction + verification) + quality check (banned-phrase scan)
        ↓
   stored back on matches table → reviewed in the frontend
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
| Drafting | CrewAI (Researcher → Drafter → Refiner agents, Groq LLM via LiteLLM) |
| Faithfulness eval | Custom claim-extraction + per-claim verification (LangChain + Groq) |
| Quality eval | Banned-phrase scan (deterministic, no LLM call) |
| Frontend | React + Vite + Tailwind |

## Repo structure

```
jobhunter/
├── resume.txt                # plain-text resume, chunked automatically by embed.py
├── backend/
│   ├── pipeline/
│   │   ├── embed.py           # embeds resume + postings via BGE
│   │   ├── score.py           # hybrid scoring: vector + BM25 + cross-encoder
│   │   └── run_phase3.py      # orchestrates embed → score → store
│   ├── fetchers/               # Adzuna + Himalayas scrapers (Phase 2)
│   ├── draft.py                # CrewAI drafting crew (Phase 4)
│   ├── evaluate.py             # faithfulness + quality checks (Phase 4)
│   ├── run_phase4.py           # orchestrates draft → evaluate → store (Phase 4)
│   └── .env
└── frontend/
    ├── index.html
    ├── package.json
    ├── tailwind.config.js
    └── src/
        ├── pages/               # MatchesDashboard, (MatchDetail — in progress)
        ├── components/          # MatchCard, ScoreBadge, StatusPill
        ├── data/                # mock data (being replaced by lib/supabaseClient.js)
        └── lib/                 # Supabase client, read-only via anon key
```

## Setup

1. Create a `.env` file **inside `backend/`** with:
   ```
   SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
   SUPABASE_KEY=your_supabase_service_key
   GROQ_API_KEY=your_groq_key
   TAVILY_API_KEY=your_tavily_key
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
   python run_phase4.py
   ```
5. For the frontend, see `frontend/README.md` (or the setup notes in this repo's Phase 5 section once added).

## Progress

- **Phase 1** — Supabase schema deployed (`postings`, `profile`, `matches`, `applications`). ✅
- **Phase 2** — Adzuna + Himalayas fetchers live; Upwork RSS and other sources dropped (broken/off-topic feeds). ✅
- **Phase 3** — Resume + postings embedded, hybrid scoring (vector + BM25 + cross-encoder) working, top 5 matches stored per run. ✅ See `PHASE3_NOTES.md` for the full debugging log.
- **Phase 4** — CrewAI drafting crew (Researcher → Drafter → Refiner, sequential) writes cover letters; faithfulness check (claim-by-claim verification against resume) and quality check (banned-phrase scan) run automatically before a draft is considered reviewable. ✅
- **Phase 5** — React frontend to browse matches and review drafts without needing to query Supabase directly. 🔜 In progress — Matches Dashboard built, Match Detail page next.
- **Phase 6** — Deployment (private access only). 🔜 Planned.

## Known limitations

- Cross-encoder raw scores are always deeply negative (model trained on
  search-query/passage pairs, not resume/job pairs) — ranking is trustworthy,
  the raw number isn't. Top-5 selection is used instead of an absolute
  score threshold.
- Top-5 has no minimum quality floor — if no postings are genuinely good
  matches, the 5 least-bad ones still get stored.
- Faithfulness scoring auto-passes (defaults to 1.0) if zero claims are
  extracted from a draft — a very short or vague letter could technically
  "pass" without there being much to actually check.
- The CrewAI drafting crew currently requires a manual workaround for a
  known CrewAI bug (`cache_breakpoint` sent to non-Anthropic providers,
  e.g. Groq) — see the monkey-patch in `draft.py`'s imports.
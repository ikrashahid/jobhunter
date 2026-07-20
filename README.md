# Job Copilot (Jobhunter)

Personal automation pipeline that scrapes job listings, scores them against a resume using hybrid vector + keyword search, drafts tailored cover letters (or interview prep when no letter is needed), fact-checks its own drafts, and exposes everything in a private Next.js dashboard.

**Status:** Phases 1–5 are working end-to-end. Auth gate is partially scaffolded. Deployment hardening is next.

---

## How it works

```
Job boards (Adzuna, Himalayas, RemoteOK, Arbeitnow, Jobicy)
        ↓
   scrapers/ → Supabase (postings)
        ↓
   resume.txt → embedded → Supabase (profile)
        ↓
   pgvector similarity + BM25 keyword search
        ↓
   Reciprocal Rank Fusion → top candidates
        ↓
   cross-encoder re-ranking → shortlist (matches)
        ↓
   If JD asks for a cover letter:
     CrewAI drafting crew (Researcher → Drafter → Refiner)
     → faithfulness + quality checks
   Else:
     interview prep (questions + answer hints)
        ↓
   FastAPI backend → Next.js frontend (review, label, track applications)
```

---

## Stack

| Layer | Tool |
|---|---|
| Database | Supabase (Postgres + pgvector) |
| Job sources | Adzuna, Himalayas, RemoteOK, Arbeitnow, Jobicy |
| Embeddings | `BAAI/bge-small-en-v1.5` (local, `sentence-transformers`) |
| Keyword scoring | `rank-bm25` |
| Re-ranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Drafting | CrewAI (Researcher → Drafter → Refiner, Groq via LiteLLM) |
| Interview prep | LangChain + Groq (`llama-3.3-70b-versatile`) |
| Faithfulness eval | Claim extraction + per-claim verification (LangChain + Groq) |
| Quality eval | Banned-phrase scan (deterministic) |
| Backend API | FastAPI + Uvicorn |
| Frontend | Next.js 16 (App Router) + React 19 + Tailwind 4 + Recharts |
| Auth (in progress) | Cookie session (`jobhunter_auth` HMAC) + login API route |

---

## Repo structure

```
jobhunter/
├── resume.txt                 # plain-text resume (gitignored; required locally)
├── schema.sql                 # full Supabase schema (source of truth)
├── requirements.txt           # Python deps (pipeline + API)
├── .env                       # SUPABASE_* + GROQ_* + TAVILY_* (gitignored)
│
├── scrapers/                  # Phase 2 — fetch job boards → postings
│   ├── fetch_all_sources.py   # Adzuna + Himalayas + RemoteOK + Arbeitnow + Jobicy
│   ├── run.py                 # lighter Adzuna + Himalayas fetch (used by API trigger)
│   ├── store.py               # upsert helper (dedupe on url)
│   └── *.py                   # per-source fetchers
│
├── pipeline/                  # Phases 3–4 — embed, score, draft, evaluate
│   ├── embed.py               # resume + unembedded postings → 384-dim vectors
│   ├── score.py               # hybrid retrieval + cross-encoder rerank
│   ├── draft.py               # CrewAI cover-letter crew
│   ├── evaluate.py            # faithfulness + quality checks
│   ├── interview_prep.py      # prep path when no cover letter is required
│   ├── pipeline.py            # full Phase 3+4 tracked run
│   ├── run_phase3.py          # embed + score only
│   └── run_phase4.py          # draft + evaluate only
│
├── backend/api/               # FastAPI service the frontend talks to
│   ├── main.py                # CORS + routers
│   ├── models.py
│   ├── routes/
│   │   ├── stats.py           # GET /api/stats
│   │   ├── matches.py         # GET/PATCH /api/matches
│   │   ├── analyze.py         # POST /api/analyze-jd
│   │   ├── metrics.py         # GET /api/metrics (precision@k, faithfulness, quality)
│   │   ├── pdf.py             # PDF export helpers
│   │   └── trigger.py         # POST /api/trigger/{fetch,score,draft}
│   └── services/
│       ├── db.py
│       ├── jd_analyzer.py
│       └── pdf_gen.py
│
└── frontend/                  # Next.js App Router UI
    ├── .env.local             # NEXT_PUBLIC_API_URL + AUTH_* (gitignored)
    ├── app/
    │   ├── page.tsx           # Pipeline dashboard (stats + trigger buttons)
    │   ├── browse/            # High-score match browser + draft/prep panel
    │   ├── matches/           # Review queue + good_fit / bad_fit labels
    │   ├── applications/      # Applied roles + outcome tracking
    │   ├── analyze/           # Paste-a-JD fit analyzer
    │   ├── metrics/           # Precision@k + draft quality charts
    │   ├── login/             # Auth UI (scaffold — see Known issues)
    │   └── api/login/         # POST credentials → signed cookie
    ├── components/            # Nav, Card
    └── lib/api.ts             # fetch wrapper → FastAPI
```

---

## Frontend pages

| Route | Purpose |
|---|---|
| `/` | Pipeline dashboard — posting/match counts, score distribution, source breakdown, one-click fetch/score/draft triggers |
| `/browse` | Side-by-side browser for matches ≥ 0.5 — cover letter or interview prep on the right |
| `/matches` | Review queue — expand drafts, label `good_fit` / `bad_fit` for precision@k |
| `/applications` | Roles marked `applied` — set outcome (got role / no response / rejected) and applied date |
| `/analyze` | Paste any JD → role summary, fit analysis, interview questions |
| `/metrics` | Precision@5/@10, faithfulness/quality means, draft success stats |
| `/login` | Private gate (API route exists; page/middleware wiring incomplete — see below) |

---

## Setup

### 1. Database

Apply `schema.sql` in the Supabase SQL editor (enables `pgvector` and creates `postings`, `profile`, `matches`, `match_log`, `jd_analyses`, `pipeline_runs`, `applications`).

### 2. Backend env

Create `.env` at the **repo root** (also loaded by `pipeline/` and `scrapers/`):

```
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

Activate the `job` conda env (or any env with `requirements.txt` installed):

```bash
pip install -r requirements.txt
```

### 3. Run the pipeline

```bash
# Fetch new postings (all 5 sources)
cd scrapers && python fetch_all_sources.py

# Embed + score + draft + evaluate (full run)
cd ../pipeline && python pipeline.py

# Or run phases separately:
python run_phase3.py   # embed + score
python run_phase4.py   # draft + evaluate
```

### 4. Start the API

From the repo root (so `api` imports resolve):

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/health`

### 5. Start the frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_password
AUTH_SECRET=long-random-string
```

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Auth (current state)

Private access is started but not fully wired:

- **Done:** `POST /api/login` validates username/password with timing-safe compares, sets an HttpOnly `jobhunter_auth` cookie (HMAC of `"authenticated"` with `AUTH_SECRET`).
- **Incomplete:** `app/login/page.tsx` currently contains middleware-style proxy code instead of a login UI, and there is no `middleware.ts` at the frontend root to enforce the cookie on protected routes.

Until that is finished, treat the app as local-only (or put it behind another gate). Do not rely on the cookie gate alone in production.

**Planned hardening:**
- Move cookie check into `frontend/middleware.ts`
- Build a real `/login` form
- Keep `AUTH_*` server-only (never `NEXT_PUBLIC_`)
- Prefer `secure` cookies in production, short session TTL + rotate `AUTH_SECRET`
- Lock down FastAPI (shared secret / same-origin proxy) so the API is not open if the frontend URL leaks

---

## Progress

| Phase | What | Status |
|---|---|---|
| 1 | Supabase schema (`postings`, `profile`, `matches`, …) | ✅ `schema.sql` committed |
| 2 | Job fetchers (5 sources) | ✅ |
| 3 | Embed + hybrid score + rerank | ✅ |
| 4 | Draft / interview prep + faithfulness & quality | ✅ |
| 5 | Next.js UI + FastAPI | ✅ Dashboard, Browse, Matches, Applications, Analyze, Metrics |
| 6 | Auth gate + private deploy | 🔜 Login API exists; middleware/UI unfinished |

---

## Monitoring

| Signal | Where |
|---|---|
| Posting volume & embedding coverage | Dashboard `/` → `/api/stats` |
| Score distribution & source mix | Dashboard charts |
| Draft success / token failures | Dashboard + Metrics |
| Precision@5 / @10 | Metrics `/metrics` (needs `human_label` on Matches) |
| Faithfulness & quality means | Metrics (from `tailored_resume` JSON) |
| Why a posting was dropped | `match_log` table (`reason`, ranks, scores) |
| Last pipeline run | Intended via `pipeline_runs` — **not yet written by scripts** (schema ready) |

**How to keep quality honest:** after each scoring run, open `/matches`, expand top results, and label `good_fit` / `bad_fit`. Precision@k is meaningless until enough labels exist.

---

## Known limitations

- Cross-encoder raw scores are often deeply negative (model trained on query/passage pairs, not resume/job). Use ranking / top-k, not absolute thresholds.
- Top-k has no minimum quality floor — weak markets still produce a shortlist.
- Faithfulness defaults to pass (1.0) if zero claims are extracted from a very short draft.
- CrewAI still needs the Groq/non-Anthropic workaround in `draft.py` (`cache_breakpoint` patch).
- `pipeline_runs` is defined in `schema.sql` but not yet populated by `pipeline.py` / phase runners — dashboard `last_run` may stay empty.
- `applications` table is legacy; live tracking uses `matches.draft_status` (`applied`, etc.) plus application outcome fields.
- API trigger `/api/trigger/fetch` runs `scrapers/run.py` (Adzuna + Himalayas only), not `fetch_all_sources.py`.
- Frontend auth gate is incomplete (see Auth section).
- FastAPI CORS allows localhost + `*.vercel.app`; the API itself has no auth middleware yet.

---

## Quick reference

```bash
# Full data refresh
cd scrapers && python fetch_all_sources.py
cd ../pipeline && python pipeline.py

# API
cd backend && uvicorn api.main:app --reload --port 8000

# UI
cd frontend && npm run dev
```

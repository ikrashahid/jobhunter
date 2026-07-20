# Job Copilot (Jobhunter)

Personal automation pipeline that scrapes job listings, scores them against a resume using hybrid vector + keyword search, drafts tailored cover letters (or interview prep when no letter is needed), fact-checks its own drafts, and exposes everything in a private Next.js dashboard.

**Status:** Phases 1–5 working. Login + FastAPI shared-secret + Next.js proxy are in place. Schedule the pipeline only after Railway has `API_KEY` set.

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
| Auth | Cookie session on Next.js (`jobhunter_auth` HMAC) + FastAPI `X-API-Key` + same-origin proxy |

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
│   ├── main.py                # CORS + routers + API-key dependency
│   ├── deps.py                # require_api_key + trigger rate limit
│   ├── models.py
│   ├── routes/
│   │   ├── stats.py           # GET /api/stats
│   │   ├── matches.py         # GET/PATCH /api/matches
│   │   ├── analyze.py         # POST /api/analyze-jd
│   │   ├── metrics.py         # GET /api/metrics (precision@k, faithfulness, quality)
│   │   ├── pdf.py             # PDF export helpers
│   │   └── trigger.py         # POST /api/trigger/{fetch,score,draft} (rate-limited)
│   └── services/
│       ├── db.py
│       ├── jd_analyzer.py
│       └── pdf_gen.py
│
└── frontend/                  # Next.js App Router UI
    ├── .env.local             # BACKEND_URL + API_KEY + AUTH_* (server-only, gitignored)
    ├── proxy.ts               # Cookie gate for all pages/API except /login
    ├── app/
    │   ├── page.tsx           # Pipeline dashboard (stats + trigger buttons)
    │   ├── browse/            # High-score match browser + draft/prep panel
    │   ├── matches/           # Review queue + good_fit / bad_fit labels
    │   ├── applications/      # Applied roles + outcome tracking
    │   ├── analyze/           # Paste-a-JD fit analyzer
    │   ├── metrics/           # Precision@k + draft quality charts
    │   ├── login/             # Animated story + glass login form
    │   └── api/
    │       ├── login/         # Cookie auth
    │       ├── logout/
    │       └── [...path]/    # Server-side proxy → FastAPI (adds X-API-Key)
    ├── components/            # Nav, Card, AppShell
    └── lib/api.ts             # Browser fetch → same-origin /api/* only
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
| `/login` | Animated intro + glass username/password form |

---

## Setup

### 1. Database

Apply `schema.sql` in the Supabase SQL editor (enables `pgvector` and creates `postings`, `profile`, `matches`, `match_log`, `jd_analyses`, `pipeline_runs`, `applications`).

### 2. Backend env

Copy `.env.example` → `.env` at the **repo root** (also loaded by `pipeline/` and `scrapers/`):

```
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
API_KEY=generate-a-long-random-string
CORS_ORIGINS=http://localhost:3000
```

`API_KEY` is required — every `/api/*` route (except `/health`) rejects requests without a matching `X-API-Key` header.

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

From `backend/` (so `api` imports resolve):

```bash
cd backend
uvicorn api.main:app --reload --port 8000
```

Health check (no key): `GET http://localhost:8000/health`  
Data routes need: `X-API-Key: <same as API_KEY>`

### 5. Start the frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

`frontend/.env.local` (all **server-only** — never `NEXT_PUBLIC_` for backend):

```
BACKEND_URL=http://localhost:8000
API_KEY=same-value-as-root-env-API_KEY
AUTH_USERNAME=your_username
AUTH_PASSWORD=your_password
AUTH_SECRET=another-long-random-string
```

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The browser only talks to Next.js; Next.js adds `X-API-Key` when proxying to FastAPI.

### Deploy env checklist

| Where | Must set |
|---|---|
| Railway (FastAPI) | `API_KEY`, Supabase/Groq/etc., optional `CORS_ORIGINS=https://your-app.vercel.app`, `TRIGGER_COOLDOWN_SEC` |
| Vercel (Next.js) | `BACKEND_URL` (Railway URL), `API_KEY` (same), `AUTH_USERNAME`, `AUTH_PASSWORD`, `AUTH_SECRET` |

Do **not** set `NEXT_PUBLIC_API_URL` — that was the hole that exposed Railway to the browser.

---

## Security

Two gates, both required:

1. **Next.js cookie gate** (`proxy.ts`) — HMAC-signed HttpOnly `jobhunter_auth` cookie; timing-safe login compare; API callers get JSON 401 (not an HTML redirect).
2. **FastAPI shared secret** — every data/trigger route requires `X-API-Key` matching `API_KEY`. `/health` stays open for uptime checks only.

**Browser never sees the backend.** `lib/api.ts` calls same-origin `/api/*`. `app/api/[...path]/route.ts` forwards to `BACKEND_URL` and injects the key. Login/logout routes are more specific and are not proxied.

**CORS** is an allowlist from `CORS_ORIGINS` (default `http://localhost:3000`). No `*.vercel.app` regex. With the proxy in place, browsers shouldn't hit Railway at all — CORS is belt-and-braces.

**Triggers** (`/api/trigger/*`) additionally:
- Require the API key (same as everything else)
- Enforce a per-action cooldown (default 120s via `TRIGGER_COOLDOWN_SEC`)
- Block overlapping runs with an in-process in-flight lock

**Secrets audit:** `.env` / `.env.local` are gitignored. `git rev-list --all -- .env` is empty in this repo (never committed). If you ever rewrite history that contained secrets, rotate Supabase/Groq/Adzuna/Tavily/`API_KEY`/`AUTH_*` anyway.

**Still optional / later:**
- Wire `pipeline_runs` writers for run history
- Drop vestigial `applications` table once confirmed unused
- `pip-audit` / `npm audit` on a schedule
- RLS on Supabase is optional while only the service-role backend touches Postgres

**Ops:** commit/tag before pipeline changes that write production `matches`/`postings`. Schedule fetch→score→draft (Railway cron or GitHub Actions) only with `X-API-Key`, never against an open URL.

---

## Progress

| Phase | What | Status |
|---|---|---|
| 1 | Supabase schema (`postings`, `profile`, `matches`, …) | ✅ `schema.sql` committed |
| 2 | Job fetchers (5 sources) | ✅ |
| 3 | Embed + hybrid score + rerank | ✅ |
| 4 | Draft / interview prep + faithfulness & quality | ✅ |
| 5 | Next.js UI + FastAPI | ✅ Dashboard, Browse, Matches, Applications, Analyze, Metrics |
| 6 | Auth + API lockdown | ✅ Cookie gate, animated login, `X-API-Key`, Next.js proxy, pinned CORS, trigger cooldown |

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
- Trigger rate limits are in-process (per Railway worker) — fine for a single instance.

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

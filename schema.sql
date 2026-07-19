-- Job Hunter — full schema
-- Reconstructed from actual column usage across pipeline/, backend/api/, and
-- scrapers/ — this is the missing source of truth referenced everywhere else
-- in the docs but never previously committed.
--
-- Requires the pgvector extension:
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────
-- postings — raw job listings from all 5 fetchers
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,                  -- 'adzuna' | 'himalayas' | 'remoteok' | 'arbeitnow' | 'jobicy'
    kind TEXT DEFAULT 'job',
    title TEXT NOT NULL,
    company TEXT,
    description TEXT,
    url TEXT NOT NULL,
    pay_range TEXT,
    location TEXT,
    posted_at TIMESTAMPTZ,
    embedding VECTOR(384),                 -- BGE small, 384-dim
    description_word_count INT,            -- powers the coverage metric
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE postings ADD CONSTRAINT IF NOT EXISTS postings_url_unique UNIQUE (url);
CREATE INDEX IF NOT EXISTS idx_postings_source ON postings(source);
CREATE INDEX IF NOT EXISTS idx_postings_embedding ON postings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ─────────────────────────────────────────────────────────────
-- profile — the embedded resume (single row, label = 'main')
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label TEXT NOT NULL,
    content TEXT NOT NULL,                 -- full resume text
    sections JSONB,                        -- chunked sections (experience, skills, etc.)
    embedding VECTOR(384),
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE profile ADD CONSTRAINT IF NOT EXISTS profile_label_unique UNIQUE (label);

-- ─────────────────────────────────────────────────────────────
-- matches — top-5 scored postings per run, plus draft + eval data
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    posting_id UUID REFERENCES postings(id),
    score FLOAT NOT NULL,                  -- final_score from cross-encoder rerank
    draft TEXT,                            -- cover letter text, or "[INTERVIEW PREP]\n\n<json>"
    draft_status TEXT DEFAULT 'pending',   -- 'pending' | 'drafted' | 'failed_token_limit' | 'failed_other'
                                            -- also reused for manual review status:
                                            -- 'unseen' | 'reviewing' | 'applied' | 'rejected'
    draft_attempts INT DEFAULT 0,
    token_estimate INT,                    -- set when draft_status = 'failed_token_limit'
    tailored_resume TEXT,                  -- JSON blob: faithfulness/quality scores + verdicts,
                                            -- OR { output_type: 'interview_prep', prep: {...} }
    human_label TEXT,                      -- 'good_fit' | 'bad_fit' — manual labels for precision@k
    notified BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE matches ADD CONSTRAINT IF NOT EXISTS matches_posting_id_unique UNIQUE (posting_id);
CREATE INDEX IF NOT EXISTS idx_matches_score ON matches(score DESC);
CREATE INDEX IF NOT EXISTS idx_matches_draft_status ON matches(draft_status);

-- ─────────────────────────────────────────────────────────────
-- match_log — every posting CONSIDERED in a scoring run, with a reason
-- if it didn't make the top 5. Powers the "why didn't this match" panel.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS match_log (
    id BIGSERIAL PRIMARY KEY,
    posting_id UUID REFERENCES postings(id),
    run_at TIMESTAMPTZ DEFAULT now(),
    vector_rank INT,
    bm25_rank INT,
    rrf_score FLOAT,
    cross_encoder_score FLOAT,
    final_score FLOAT,
    selected BOOLEAN NOT NULL,
    reason TEXT NOT NULL,                  -- 'selected' | 'thin_description' |
                                            -- 'rrf_ranked_below_top20' | 'cross_encoder_ranked_below_top5'
    description_word_count INT
);

CREATE INDEX IF NOT EXISTS idx_match_log_posting ON match_log(posting_id);
CREATE INDEX IF NOT EXISTS idx_match_log_run_at ON match_log(run_at);

-- ─────────────────────────────────────────────────────────────
-- jd_analyses — results of the paste-a-JD analyzer feature
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jd_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jd_text TEXT NOT NULL,
    role_summary JSONB,
    fit_analysis JSONB,
    interview_questions JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_jd_analyses_created ON jd_analyses(created_at DESC);

-- ─────────────────────────────────────────────────────────────
-- pipeline_runs — NOT YET WRITTEN TO BY ANY SCRIPT (see README Known
-- Issues). Table defined here so the schema is ready once run-logging
-- is added to pipeline.py / run_phase3.py / run_phase4.py.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    postings_embedded INT,
    matches_scored INT,
    drafts_attempted INT,
    drafts_succeeded INT,
    drafts_failed INT,
    status TEXT DEFAULT 'running'          -- 'running' | 'complete' | 'failed'
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started ON pipeline_runs(started_at DESC);

-- ─────────────────────────────────────────────────────────────
-- applications — legacy manual tracking table from the original 4-table
-- design. Superseded in practice by matches.draft_status doubling as a
-- review-status field (unseen/reviewing/applied/rejected) — kept here
-- for compatibility but likely safe to drop once confirmed unused.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID REFERENCES matches(id),
    status TEXT,
    applied_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
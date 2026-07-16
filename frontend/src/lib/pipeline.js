import { supabase } from "./supabaseClient";

/**
 * Pulls everything the Pipeline Overview page needs in one place:
 * posting counts, coverage, source breakdown, match_log reasons,
 * score distribution, eval score averages, and token truncation flags.
 *
 * This does a few separate queries rather than one giant join, since
 * postings/matches/match_log serve different purposes and mixing them
 * into one query would mean re-fetching huge duplicated rows.
 */
export async function fetchPipelineStats() {
  const [postingsRes, matchesRes, matchLogRes] = await Promise.all([
    supabase.from("postings").select("id, source, description_word_count, embedding"),
    supabase.from("matches").select("id, score, draft, tailored_resume"),
    supabase.from("match_log").select("reason, final_score, description_word_count"),
  ]);

  if (postingsRes.error) throw postingsRes.error;
  if (matchesRes.error) throw matchesRes.error;
  if (matchLogRes.error) throw matchLogRes.error;

  const postings = postingsRes.data ?? [];
  const matches = matchesRes.data ?? [];
  const matchLog = matchLogRes.data ?? [];

  // ── Pipeline counts ──────────────────────────────────────
  const totalPostings = postings.length;
  const embeddedCount = postings.filter((p) => p.embedding !== null).length;
  const scoredCount = matches.length;
  const draftedCount = matches.filter((m) => !!m.draft).length;

  // ── Coverage — % of postings with enough text to embed well ──
  const THIN_THRESHOLD = 60;
  const withWordCount = postings.filter((p) => p.description_word_count !== null);
  const thinCount = withWordCount.filter(
    (p) => p.description_word_count < THIN_THRESHOLD
  ).length;
  const coveragePct = withWordCount.length
    ? Math.round(((withWordCount.length - thinCount) / withWordCount.length) * 100)
    : null;

  // ── Source breakdown ─────────────────────────────────────
  const sourceCounts = {};
  for (const p of postings) {
    const src = p.source || "unknown";
    sourceCounts[src] = (sourceCounts[src] || 0) + 1;
  }
  const sourceBreakdown = Object.entries(sourceCounts)
    .map(([source, count]) => ({ source, count }))
    .sort((a, b) => b.count - a.count);

  // ── Why-not-matched reasons (from match_log) ─────────────
  const reasonCounts = {};
  for (const row of matchLog) {
    reasonCounts[row.reason] = (reasonCounts[row.reason] || 0) + 1;
  }
  const reasonBreakdown = Object.entries(reasonCounts)
    .map(([reason, count]) => ({ reason, count }))
    .sort((a, b) => b.count - a.count);

  // ── Score distribution histogram (0.0–1.0 in 0.1 buckets) ──
  const buckets = Array.from({ length: 10 }, (_, i) => ({
    range: `${(i / 10).toFixed(1)}–${((i + 1) / 10).toFixed(1)}`,
    count: 0,
  }));
  for (const row of matchLog) {
    if (row.final_score === null || row.final_score === undefined) continue;
    const idx = Math.min(Math.floor(row.final_score * 10), 9);
    buckets[idx].count += 1;
  }

  // ── Eval score averages (faithfulness + quality) ─────────
  const evaluated = matches
    .map((m) => {
      if (!m.tailored_resume) return null;
      try {
        return JSON.parse(m.tailored_resume);
      } catch {
        return null;
      }
    })
    .filter(Boolean);

  const avg = (nums) =>
    nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;

  const faithfulnessScores = evaluated
    .map((e) => e.faithfulness_score)
    .filter((v) => typeof v === "number");
  const qualityScores = evaluated
    .map((e) => e.quality_score)
    .filter((v) => typeof v === "number");

  // ── Token truncation log ─────────────────────────────────
  const truncated = evaluated.filter((e) => e.job_description_truncated === true);

  const draftFailedCount = draftedCount
    ? Math.max(0, scoredCount - draftedCount)
    : 0;

  return {
    totalPostings,
    embeddedCount,
    scoredCount,
    draftedCount,
    draftFailedCount,
    coveragePct,
    thinCount,
    sourceBreakdown,
    reasonBreakdown,
    scoreDistribution: buckets,
    avgFaithfulness: avg(faithfulnessScores),
    avgQuality: avg(qualityScores),
    truncatedCount: truncated.length,
    evaluatedCount: evaluated.length,
  };
}

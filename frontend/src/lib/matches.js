import { supabase } from "./supabaseClient";

/**
 * Parses the tailored_resume column, which stores the Phase 4 eval
 * output as a JSON string (see evaluate.py / run_phase4.py). Returns
 * null if there's nothing to parse yet (match hasn't been drafted).
 */
function parseEval(tailoredResumeRaw) {
  if (!tailoredResumeRaw) return null;
  try {
    const parsed = JSON.parse(tailoredResumeRaw);
    return {
      faithfulness_score: parsed.faithfulness_score ?? null,
      quality_score: parsed.quality_score ?? null,
      verdicts: parsed.verdicts ?? [],
      banned_found: parsed.banned_phrases_found ?? [],
      company_research: parsed.company_research ?? "",
    };
  } catch (err) {
    console.error("Failed to parse tailored_resume JSON for a match:", err);
    return null;
  }
}

/**
 * Normalizes one raw Supabase row (matches joined with postings) into
 * the shape the UI components expect.
 */
function normalizeMatch(row) {
  return {
    id: row.id,
    score: row.score,
    draft: row.draft,
    posting: {
      title: row.postings?.title ?? "Untitled role",
      company: row.postings?.company ?? "Unknown company",
      description: row.postings?.description ?? "",
      url: row.postings?.url ?? "#",
    },
    eval: parseEval(row.tailored_resume),
  };
}

/**
 * Fetches all matches, newest/highest score first, joined with their
 * posting details. Mirrors the query shape used in run_phase4.py.
 */
export async function fetchMatches() {
  const { data, error } = await supabase
    .from("matches")
    .select(
      "id, score, draft, tailored_resume, postings ( title, company, description, url )"
    )
    .order("score", { ascending: false });

  if (error) throw error;
  return data.map(normalizeMatch);
}

/**
 * Fetches a single match by id, with the same shape as fetchMatches.
 */
export async function fetchMatchById(id) {
  const { data, error } = await supabase
    .from("matches")
    .select(
      "id, score, draft, tailored_resume, postings ( title, company, description, url )"
    )
    .eq("id", id)
    .single();

  if (error) throw error;
  return normalizeMatch(data);
}

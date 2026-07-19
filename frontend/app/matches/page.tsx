"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Card from "@/components/Card";

interface Match {
  id: string;
  score: number;
  draft: string | null;
  draft_status: string | null;
  output_type: string | null;
  human_label: string | null;
  tailored_resume: string | null;
  postings: {
    title: string;
    company: string;
    description: string;
    url: string;
    source: string;
    pay_range: string | null;
    location: string | null;
  };
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? "var(--green)" : pct >= 60 ? "var(--amber)" : "var(--red)";
  return (
    <span style={{
      background: color + "22",
      color,
      border: `1px solid ${color}44`,
      borderRadius: 4,
      padding: "2px 8px",
      fontSize: 12,
      fontWeight: 600,
    }}>
      {pct}%
    </span>
  );
}

function StatusBadge({ status }: { status: string | null }) {
  const map: Record<string, { label: string; color: string }> = {
    drafted: { label: "Drafted", color: "var(--green)" },
    pending: { label: "Pending", color: "var(--amber)" },
    failed_token_limit: { label: "Token Limit", color: "var(--red)" },
    failed_other: { label: "Failed", color: "var(--red)" },
  };
  const s = map[status || "pending"] || { label: status || "pending", color: "var(--text-muted)" };
  return (
    <span style={{
      background: s.color + "22",
      color: s.color,
      borderRadius: 4,
      padding: "2px 8px",
      fontSize: 11,
    }}>
      {s.label}
    </span>
  );
}

export default function MatchesPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [labeling, setLabeling] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/matches?per_page=10")
      .then(d => setMatches(d.matches || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function label(id: string, value: string) {
    setLabeling(id);
    try {
      await api.patch(`/api/matches/${id}`, { human_label: value });
      setMatches(prev => prev.map(m => m.id === id ? { ...m, human_label: value } : m));
    } finally {
      setLabeling(null);
    }
  }

  async function updateStatus(id: string, status: string) {
    await api.patch(`/api/matches/${id}`, { status });
    setMatches(prev => prev.map(m => m.id === id ? { ...m, draft_status: status } : m));
  }

  function getMeta(match: Match) {
    try {
      return JSON.parse(match.tailored_resume || "{}");
    } catch { return {}; }
  }

  function renderDraft(match: Match) {
    const meta = getMeta(match);
    const outputType = meta.output_type || match.output_type || "cover_letter";

    if (outputType === "interview_prep") {
      const prep = meta.prep || {};
      const questions = prep.questions || {};
      return (
        <div>
          <div style={{ color: "var(--accent)", fontSize: 12, fontWeight: 600, marginBottom: 12 }}>
            INTERVIEW PREP
          </div>
          {prep.focus_areas?.role_in_one_line && (
            <div style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 16, fontStyle: "italic" }}>
              {prep.focus_areas.role_in_one_line}
            </div>
          )}
          {["technical", "behavioral", "role_specific"].map(type => (
            <div key={type} style={{ marginBottom: 16 }}>
              <div style={{ fontWeight: 600, fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8 }}>
                {type.replace("_", " ")}
              </div>
              {(questions[type] || []).map((q: { question: string; answer_from_resume: string; what_they_test: string }, idx: number) => (
                <div key={idx} style={{ marginBottom: 12, padding: "10px 12px", background: "var(--surface2)", borderRadius: 6 }}>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>{q.question}</div>
                  <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{q.what_they_test}</div>
                  <div style={{ fontSize: 12, color: "var(--accent)", marginTop: 6 }}>→ {q.answer_from_resume}</div>
                </div>
              ))}
            </div>
          ))}
          {(questions.questions_to_ask_them || []).length > 0 && (
            <div>
              <div style={{ fontWeight: 600, fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8 }}>
                Ask them
              </div>
              {questions.questions_to_ask_them.map((q: string, idx: number) => (
                <div key={idx} style={{ fontSize: 13, padding: "6px 0", borderBottom: "1px solid var(--border)" }}>
                  • {q}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Cover letter mode
    return (
      <div>
        <div style={{ color: "var(--accent)", fontSize: 12, fontWeight: 600, marginBottom: 12 }}>
          COVER LETTER
        </div>
        <div style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.7, marginBottom: 16 }}>
          {match.draft}
        </div>
        {meta.faithfulness_score !== undefined && (
          <div style={{ display: "flex", gap: 16, padding: "10px 0", borderTop: "1px solid var(--border)" }}>
            <div style={{ fontSize: 12 }}>
              <span style={{ color: "var(--text-muted)" }}>Faithfulness: </span>
              <span style={{ color: meta.faithfulness_score >= 0.8 ? "var(--green)" : "var(--red)", fontWeight: 600 }}>
                {Math.round((meta.faithfulness_score || 0) * 100)}%
              </span>
            </div>
            <div style={{ fontSize: 12 }}>
              <span style={{ color: "var(--text-muted)" }}>Quality: </span>
              <span style={{ color: (meta.quality_score || 0) >= 0.8 ? "var(--green)" : "var(--amber)", fontWeight: 600 }}>
                {Math.round((meta.quality_score || 0) * 100)}%
              </span>
            </div>
          </div>
        )}
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
            <a
            href={`${api.BASE}/api/matches/${match.id}/pdf/cover-letter`}
            target="_blank"
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              background: "var(--accent)",
              color: "#fff",
              fontSize: 12,
              textDecoration: "none",
              fontWeight: 500,
            }}
          >
            Download Cover Letter PDF
          </a>
            <a
            href={`${api.BASE}/api/matches/${match.id}/pdf/fit`}
            target="_blank"
            style={{
              padding: "6px 14px",
              borderRadius: 6,
              border: "1px solid var(--border)",
              color: "var(--text)",
              fontSize: 12,
              textDecoration: "none",
            }}
          >
            Download Fit Report PDF
          </a>
        </div>
      </div>
    );
  }

  if (loading) return <div style={{ color: "var(--text-muted)", padding: 40 }}>Loading matches...</div>;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Top Matches</h1>
        <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
          {matches.length} matches — click any row to expand
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {matches.map(match => (
          <Card key={match.id} style={{ cursor: "pointer" }}>
            <div
              onClick={() => setExpanded(expanded === match.id ? null : match.id)}
              style={{ display: "flex", alignItems: "center", gap: 12 }}
            >
              <ScoreBadge score={match.score} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>
                  {match.postings?.title}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                  {match.postings?.company}
                  {match.postings?.location ? ` · ${match.postings.location}` : ""}
                  {match.postings?.pay_range ? ` · ${match.postings.pay_range}` : ""}
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{
                  fontSize: 11,
                  color: "var(--text-muted)",
                  background: "var(--surface2)",
                  padding: "2px 6px",
                  borderRadius: 4,
                }}>
                  {match.postings?.source}
                </span>
                <StatusBadge status={match.draft_status} />
                <span style={{ fontSize: 16, color: "var(--text-muted)" }}>
                  {expanded === match.id ? "▲" : "▼"}
                </span>
              </div>
            </div>

            {expanded === match.id && (
              <div style={{ marginTop: 20, borderTop: "1px solid var(--border)", paddingTop: 20 }}>
                <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
                    <a
                    href={match.postings?.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      padding: "5px 12px",
                      borderRadius: 6,
                      border: "1px solid var(--border)",
                      color: "var(--text)",
                      fontSize: 12,
                      textDecoration: "none",
                    }}
                  >
                    View Job Posting ↗
                  </a>

                  {["unseen", "reviewing", "applied", "rejected"].map(s => (
                    <button
                      key={s}
                      onClick={() => updateStatus(match.id, s)}
                      style={{
                        padding: "5px 12px",
                        borderRadius: 6,
                        border: "1px solid var(--border)",
                        background: match.draft_status === s ? "var(--accent)" : "var(--surface2)",
                        color: match.draft_status === s ? "#fff" : "var(--text-muted)",
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                    >
                      {s}
                    </button>
                  ))}

                  <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
                    <span style={{ fontSize: 12, color: "var(--text-muted)", alignSelf: "center" }}>
                      Label:
                    </span>
                    {[
                      { value: "good_fit", label: "👍 Good fit", color: "var(--green)" },
                      { value: "bad_fit", label: "👎 Bad fit", color: "var(--red)" },
                    ].map(opt => (
                      <button
                        key={opt.value}
                        onClick={() => label(match.id, opt.value)}
                        disabled={labeling === match.id}
                        style={{
                          padding: "5px 12px",
                          borderRadius: 6,
                          border: `1px solid ${opt.color}44`,
                          background: match.human_label === opt.value ? opt.color + "33" : "transparent",
                          color: opt.color,
                          fontSize: 12,
                          cursor: "pointer",
                          fontWeight: match.human_label === opt.value ? 700 : 400,
                        }}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>

                {match.draft ? (
                  renderDraft(match)
                ) : (
                  <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "20px 0" }}>
                    {match.draft_status === "failed_token_limit"
                      ? "Draft skipped — job description too long for current token limit. Will retry automatically."
                      : "Draft not yet generated. Run the draft pipeline from the dashboard."}
                  </div>
                )}
              </div>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
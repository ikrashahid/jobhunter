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
      flexShrink: 0,
    }}>
      {pct}%
    </span>
  );
}

export default function BrowsePage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/matches?min_score=0.5&per_page=100")
      .then(d => {
        const list: Match[] = d.matches || [];
        setMatches(list);
        if (list.length > 0) setSelectedId(list[0].id);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const selected = matches.find(m => m.id === selectedId) || null;

  function getMeta(match: Match) {
    try {
      return JSON.parse(match.tailored_resume || "{}");
    } catch { return {}; }
  }

  function renderRight(match: Match) {
    const meta = getMeta(match);
    const outputType = meta.output_type || match.output_type || "cover_letter";
    const prep = meta.prep || {};
    const questions = prep.questions || {};
    const hasQuestions = outputType === "interview_prep" && Object.keys(questions).length > 0;

    return (
      <div>
        <div style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700 }}>{match.postings?.title}</h2>
          <div style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>
            {match.postings?.company}
            {match.postings?.location ? ` · ${match.postings.location}` : ""}
            {match.postings?.pay_range ? ` · ${match.postings.pay_range}` : ""}
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
          <a
            href={match.postings?.url}
            target="_blank"
            rel="noreferrer"
            style={{
              padding: "7px 16px",
              borderRadius: 6,
              background: "var(--accent)",
              color: "#fff",
              fontSize: 13,
              textDecoration: "none",
              fontWeight: 500,
            }}
          >
            Apply / View Posting ↗
          </a>
        </div>

        <div style={{ marginBottom: 24 }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8 }}>
            Job Description
          </div>
          <div style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.7, maxHeight: 320, overflowY: "auto", padding: "12px 14px", background: "var(--surface2)", borderRadius: 6 }}>
            {match.postings?.description || "No description available."}
          </div>
        </div>

        {hasQuestions ? (
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8 }}>
              Interview Questions
            </div>
            {["technical", "behavioral", "role_specific"].map(type => (
              (questions[type] || []).length > 0 && (
                <div key={type} style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 6 }}>
                    {type.replace("_", " ")}
                  </div>
                  {questions[type].map((q: { question: string; answer_from_resume: string }, idx: number) => (
                    <div key={idx} style={{ marginBottom: 10, padding: "10px 12px", background: "var(--surface2)", borderRadius: 6 }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>{q.question}</div>
                      <div style={{ fontSize: 12, color: "var(--accent)" }}>→ {q.answer_from_resume}</div>
                    </div>
                  ))}
                </div>
              )
            ))}
          </div>
        ) : match.draft ? (
          <div>
            <div style={{ fontWeight: 600, fontSize: 12, color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8 }}>
              Cover Letter Draft
            </div>
            <div style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.7, padding: "12px 14px", background: "var(--surface2)", borderRadius: 6 }}>
              {match.draft}
            </div>
          </div>
        ) : (
          <div style={{ color: "var(--text-muted)", fontSize: 13 }}>
            No draft or questions generated for this one yet.
          </div>
        )}
      </div>
    );
  }

  if (loading) return <div style={{ color: "var(--text-muted)", padding: 40 }}>Loading matches...</div>;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div className="page-kicker">From campus to inbox</div>
        <h1 className="page-title">Browse Matches</h1>
        <p className="page-sub">
          {matches.length} matches at 50%+ — open a role to review the draft or interview prep
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 20, alignItems: "start" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: "calc(100vh - 160px)", overflowY: "auto" }}>
          {matches.map(match => (
            <div
              key={match.id}
              onClick={() => setSelectedId(match.id)}
              style={{
                cursor: "pointer",
                padding: "12px 14px",
                borderRadius: 8,
                border: `1px solid ${selectedId === match.id ? "var(--accent)" : "var(--border)"}`,
                background: selectedId === match.id ? "var(--surface2)" : "var(--surface)",
                display: "flex",
                alignItems: "center",
                gap: 10,
              }}
            >
              <ScoreBadge score={match.score} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {match.postings?.title}
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {match.postings?.company}
                </div>
              </div>
            </div>
          ))}
          {matches.length === 0 && (
            <div style={{ color: "var(--text-muted)", fontSize: 13, padding: 20 }}>
              No matches at 50%+ yet.
            </div>
          )}
        </div>

        <Card style={{ position: "sticky", top: 20, maxHeight: "calc(100vh - 160px)", overflowY: "auto" }}>
          {selected ? renderRight(selected) : (
            <div style={{ color: "var(--text-muted)", fontSize: 13 }}>Select a job from the left.</div>
          )}
        </Card>
      </div>
    </div>
  );
}
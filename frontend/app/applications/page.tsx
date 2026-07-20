"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Card from "@/components/Card";

interface Match {
  id: string;
  score: number;
  application_status: string | null; // 'red' | 'yellow' | 'green'
  applied_at: string | null;
  postings: {
    title: string;
    company: string;
    url: string;
  };
}

const STATUS_OPTS = [
  { value: "green", label: "Got a role", color: "var(--green)" },
  { value: "yellow", label: "No response", color: "var(--amber)" },
  { value: "red", label: "Rejected", color: "var(--red)" },
];

export default function ApplicationsPage() {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);

  useEffect(() => {
    // "applied" here is draft_status, set from the Matches/Browse page
    // buttons — this list is just those, in one place.
    api.get("/api/matches?status=applied&per_page=200")
      .then(d => setMatches(d.matches || []))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  async function setStatus(id: string, application_status: string) {
    setSavingId(id);
    try {
      await api.patch(`/api/matches/${id}`, { application_status });
      setMatches(prev => prev.map(m => m.id === id ? { ...m, application_status } : m));
    } finally {
      setSavingId(null);
    }
  }

  async function setDate(id: string, dateStr: string) {
    setSavingId(id);
    try {
      // dateStr from <input type="date"> is 'YYYY-MM-DD'; send as ISO.
      const iso = dateStr ? new Date(dateStr).toISOString() : null;
      await api.patch(`/api/matches/${id}`, { applied_at: iso });
      setMatches(prev => prev.map(m => m.id === id ? { ...m, applied_at: iso } : m));
    } finally {
      setSavingId(null);
    }
  }

  if (loading) return <div style={{ color: "var(--text-muted)", padding: 40 }}>Loading applications...</div>;

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div className="page-kicker">Out in the wild</div>
        <h1 className="page-title">Applications</h1>
        <p className="page-sub">
          {matches.length} roles marked applied — track outcome and date here
        </p>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {matches.map(match => (
          <Card key={match.id}>
            <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
              <div style={{ flex: 1, minWidth: 200 }}>
                <a
                  href={match.postings?.url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ fontWeight: 600, fontSize: 14, color: "var(--text)", textDecoration: "none" }}
                >
                  {match.postings?.title}
                </a>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                  {match.postings?.company}
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Applied on</span>
                <input
                  type="date"
                  value={match.applied_at ? match.applied_at.slice(0, 10) : ""}
                  onChange={e => setDate(match.id, e.target.value)}
                  disabled={savingId === match.id}
                  style={{
                    background: "var(--surface2)",
                    border: "1px solid var(--border)",
                    borderRadius: 6,
                    color: "var(--text)",
                    padding: "5px 8px",
                    fontSize: 12,
                  }}
                />
              </div>

              <div style={{ display: "flex", gap: 6 }}>
                {STATUS_OPTS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setStatus(match.id, opt.value)}
                    disabled={savingId === match.id}
                    title={opt.label}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 6,
                      border: `1px solid ${opt.color}44`,
                      background: match.application_status === opt.value ? opt.color + "33" : "transparent",
                      color: opt.color,
                      fontSize: 12,
                      fontWeight: match.application_status === opt.value ? 700 : 400,
                      cursor: "pointer",
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </Card>
        ))}

        {matches.length === 0 && (
          <div style={{ color: "var(--text-muted)", fontSize: 13, padding: 20 }}>
            Nothing here yet — mark a job "applied" on the Matches or Browse page and it'll show up here.
          </div>
        )}
      </div>
    </div>
  );
}
"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Card from "@/components/Card";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell
} from "recharts";

interface Stats {
  postings: { total: number; embedded: number; embedding_coverage: number };
  matches: { total: number; drafted: number; failed_token_limit: number; pending: number; draft_success_rate: number };
  scores: { average: number; distribution: Record<string, number> };
  sources: Record<string, number>;
  last_run: string | null;
}

function StatCard({ label, value, sub, color }: {
  label: string; value: string | number; sub?: string; color?: string;
}) {
  return (
    <Card>
      <div style={{ color: "var(--text-muted)", fontSize: 12, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color: color || "var(--text)" }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>{sub}</div>}
    </Card>
  );
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState<string | null>(null);

  useEffect(() => {
    api.get("/api/stats")
      .then(setStats)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function trigger(action: string) {
    setTriggering(action);
    try {
      await api.post(`/api/trigger/${action}`, {});
      const fresh = await api.get("/api/stats");
      setStats(fresh);
    } catch (e: unknown) {
      alert(`Trigger failed: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setTriggering(null);
    }
  }

  if (loading) return (
    <div style={{ color: "var(--text-muted)", padding: 40, textAlign: "center" }}>
      Loading pipeline data...
    </div>
  );
  if (error) return (
    <div style={{ color: "var(--red)", padding: 40 }}>
      Could not reach backend: {error}
    </div>
  );
  if (!stats) return null;

  const distData = Object.entries(stats.scores.distribution).map(([range, count]) => ({
    range, count,
  }));

  const sourceData = Object.entries(stats.sources).map(([source, count]) => ({
    source, count,
  }));

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Pipeline Dashboard</h1>
          <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
            {stats.last_run
              ? `Last run: ${new Date(stats.last_run).toLocaleString()}`
              : "No pipeline runs recorded yet"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {["fetch", "score", "draft"].map(action => (
            <button
              key={action}
              onClick={() => trigger(action)}
              disabled={triggering !== null}
              style={{
                padding: "8px 16px",
                borderRadius: 6,
                border: "1px solid var(--border)",
                background: triggering === action ? "var(--accent)" : "var(--surface2)",
                color: "var(--text)",
                cursor: triggering !== null ? "not-allowed" : "pointer",
                fontSize: 12,
                fontWeight: 500,
              }}
            >
              {triggering === action ? "Running..." : `Run ${action}`}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 24 }}>
        <StatCard
          label="Total Postings"
          value={stats.postings.total}
          sub={`${stats.postings.embedded} embedded`}
        />
        <StatCard
          label="Embedding Coverage"
          value={`${Math.round(stats.postings.embedding_coverage * 100)}%`}
          sub={`${stats.postings.total - stats.postings.embedded} remaining`}
          color={stats.postings.embedding_coverage > 0.8 ? "var(--green)" : "var(--amber)"}
        />
        <StatCard
          label="Matches Scored"
          value={stats.matches.total}
          sub={`${stats.matches.drafted} drafted`}
          color="var(--accent)"
        />
        <StatCard
          label="Draft Success Rate"
          value={`${Math.round(stats.matches.draft_success_rate * 100)}%`}
          sub={`${stats.matches.failed_token_limit} token failures`}
          color={stats.matches.draft_success_rate > 0.8 ? "var(--green)" : "var(--amber)"}
        />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 24 }}>
        <Card>
          <div style={{ fontWeight: 600, marginBottom: 16 }}>Score Distribution</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={distData}>
              <XAxis dataKey="range" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
              <YAxis tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
              <Tooltip
                contentStyle={{
                  background: "var(--surface2)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                  color: "var(--text)",
                }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {distData.map((_, i) => (
                  <Cell key={i} fill={i >= 3 ? "var(--accent)" : "var(--surface2)"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <div style={{ fontWeight: 600, marginBottom: 16 }}>Postings by Source</div>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={sourceData} layout="vertical">
              <XAxis type="number" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
              <YAxis
                dataKey="source"
                type="category"
                tick={{ fontSize: 11, fill: "var(--text-muted)" }}
                width={90}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--surface2)",
                  border: "1px solid var(--border)",
                  borderRadius: 6,
                }}
              />
              <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card>
        <div style={{ fontWeight: 600, marginBottom: 16 }}>Match Summary</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {[
            { label: "Average Score", value: `${Math.round(stats.scores.average * 100)}%` },
            { label: "Total Matches", value: stats.matches.total },
            { label: "Pending Drafts", value: stats.matches.pending },
            { label: "Token Failures", value: stats.matches.failed_token_limit },
          ].map(item => (
            <div key={item.label} style={{ textAlign: "center", padding: "8px 0" }}>
              <div style={{ fontSize: 26, fontWeight: 700, color: "var(--accent)" }}>
                {item.value}
              </div>
              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                {item.label}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

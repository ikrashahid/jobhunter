"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Card from "@/components/Card";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer
} from "recharts";

interface Metrics {
  precision: { at_5: number | null; at_10: number | null; labeled_count: number; good_fit_count: number };
  faithfulness: { mean: number | null; min: number | null; max: number | null; sample_count: number };
  quality: { mean: number | null; min: number | null; max: number | null; sample_count: number };
  pipeline: { draft_success_count: number; token_failure_count: number; total_matches: number };
}

function MetricBlock({ label, value, sub, color }: {
  label: string; value: string; sub?: string; color?: string;
}) {
  return (
    <div style={{ textAlign: "center", padding: "16px 0" }}>
      <div style={{ fontSize: 32, fontWeight: 700, color: color || "var(--accent)" }}>{value}</div>
      <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/metrics")
      .then(setMetrics)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ color: "var(--text-muted)", padding: 40 }}>Loading metrics...</div>;
  if (!metrics) return null;

  const pct = (v: number | null) => v === null ? "N/A" : `${Math.round(v * 100)}%`;
  const fmt = (v: number | null) => v === null ? "N/A" : v.toFixed(3);

  const qualityData = metrics.quality.mean !== null ? [
    { label: "Min", value: metrics.quality.min || 0 },
    { label: "Mean", value: metrics.quality.mean || 0 },
    { label: "Max", value: metrics.quality.max || 0 },
  ] : [];

  const faithData = metrics.faithfulness.mean !== null ? [
    { label: "Min", value: metrics.faithfulness.min || 0 },
    { label: "Mean", value: metrics.faithfulness.mean || 0 },
    { label: "Max", value: metrics.faithfulness.max || 0 },
  ] : [];

  const noLabels = metrics.precision.labeled_count === 0;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Eval Metrics</h1>
        <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
          Label matches on the Matches page to unlock precision@k scores
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <Card>
          <div style={{ fontWeight: 600, marginBottom: 16 }}>Retrieval Quality (Precision@k)</div>
          {noLabels ? (
            <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
              No labels yet. Go to Matches and click 👍 Good fit or 👎 Bad fit on your top matches.
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              <MetricBlock
                label="Precision@5"
                value={pct(metrics.precision.at_5)}
                sub="top 5 matches"
                color={metrics.precision.at_5 && metrics.precision.at_5 >= 0.6 ? "var(--green)" : "var(--amber)"}
              />
              <MetricBlock
                label="Precision@10"
                value={pct(metrics.precision.at_10)}
                sub="top 10 matches"
                color={metrics.precision.at_10 && metrics.precision.at_10 >= 0.5 ? "var(--green)" : "var(--amber)"}
              />
            </div>
          )}
          <div style={{ borderTop: "1px solid var(--border)", paddingTop: 12, marginTop: 12, fontSize: 12, color: "var(--text-muted)" }}>
            {metrics.precision.labeled_count} labeled · {metrics.precision.good_fit_count} good fit
          </div>
        </Card>

        <Card>
          <div style={{ fontWeight: 600, marginBottom: 16 }}>Pipeline Health</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <MetricBlock
              label="Drafts Succeeded"
              value={String(metrics.pipeline.draft_success_count)}
              sub={`of ${metrics.pipeline.total_matches} matches`}
              color="var(--green)"
            />
            <MetricBlock
              label="Token Failures"
              value={String(metrics.pipeline.token_failure_count)}
              sub="auto-retried hourly"
              color={metrics.pipeline.token_failure_count > 0 ? "var(--amber)" : "var(--text-muted)"}
            />
          </div>
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Faithfulness Score Distribution</div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
            {metrics.faithfulness.sample_count} drafts evaluated · mean {fmt(metrics.faithfulness.mean)}
          </div>
          {faithData.length > 0 ? (
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={faithData}>
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                <Tooltip
                  contentStyle={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6 }}
                  formatter={(v: number) => `${Math.round(v * 100)}%`}
                />
                <Bar dataKey="value" fill="var(--green)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
              No drafts evaluated yet
            </div>
          )}
        </Card>

        <Card>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Quality Score Distribution</div>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 16 }}>
            {metrics.quality.sample_count} drafts evaluated · mean {fmt(metrics.quality.mean)}
          </div>
          {qualityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={qualityData}>
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: "var(--text-muted)" }} />
                <Tooltip
                  contentStyle={{ background: "var(--surface2)", border: "1px solid var(--border)", borderRadius: 6 }}
                  formatter={(v: number) => `${Math.round(v * 100)}%`}
                />
                <Bar dataKey="value" fill="var(--accent)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "20px 0", textAlign: "center" }}>
              No drafts evaluated yet
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import Card from "@/components/Card";

interface Analysis {
  role_summary: {
    actual_role: string;
    seniority: string;
    key_requirements: string[];
    nice_to_have: string[];
    red_flags: string[];
    remote: boolean;
  };
  fit_analysis: {
    strong_matches: { requirement: string; evidence: string; strength: string }[];
    gaps: { requirement: string; gap: string; mitigation: string }[];
    overall_fit: string;
    fit_summary: string;
  };
  interview_questions: {
    technical: { question: string; why_asked: string; your_answer_hint: string }[];
    behavioral: { question: string; why_asked: string; your_answer_hint: string }[];
    role_specific: { question: string; why_asked: string; your_answer_hint: string }[];
  };
}

export default function AnalyzePage() {
  const [jdText, setJdText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"role" | "fit" | "questions">("role");

  async function analyze() {
    if (!jdText.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.post("/api/analyze-jd", { jd_text: jdText });
      setResult(data);
      setActiveTab("role");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  const fitColor = (fit: string) =>
    fit === "strong" ? "var(--green)" : fit === "moderate" ? "var(--amber)" : "var(--red)";

  const strengthColor = (s: string) =>
    s === "strong" ? "var(--green)" : s === "moderate" ? "var(--amber)" : "var(--red)";

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 22, fontWeight: 700 }}>Analyze Job Description</h1>
        <div style={{ color: "var(--text-muted)", fontSize: 12, marginTop: 4 }}>
          Paste any JD — from LinkedIn, email, anywhere. Get role breakdown, CV fit map, and interview prep.
        </div>
      </div>

      <Card style={{ marginBottom: 20 }}>
        <textarea
          value={jdText}
          onChange={e => setJdText(e.target.value)}
          placeholder="Paste the full job description here..."
          style={{
            width: "100%",
            minHeight: 200,
            background: "var(--surface2)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: 12,
            color: "var(--text)",
            fontSize: 13,
            resize: "vertical",
            outline: "none",
            fontFamily: "inherit",
          }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12 }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {jdText.length} characters
          </span>
          <button
            onClick={analyze}
            disabled={loading || !jdText.trim()}
            style={{
              padding: "8px 20px",
              borderRadius: 6,
              background: loading ? "var(--surface2)" : "var(--accent)",
              color: "#fff",
              border: "none",
              cursor: loading || !jdText.trim() ? "not-allowed" : "pointer",
              fontSize: 13,
              fontWeight: 600,
            }}
          >
            {loading ? "Analyzing..." : "Analyze"}
          </button>
        </div>
      </Card>

      {error && (
        <div style={{ color: "var(--red)", padding: 16, background: "var(--red)11", borderRadius: 8, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {result && (
        <div>
          <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
            {(["role", "fit", "questions"] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: "8px 16px",
                  borderRadius: 6,
                  border: "1px solid var(--border)",
                  background: activeTab === tab ? "var(--accent)" : "var(--surface2)",
                  color: activeTab === tab ? "#fff" : "var(--text-muted)",
                  cursor: "pointer",
                  fontSize: 13,
                  fontWeight: activeTab === tab ? 600 : 400,
                }}
              >
                {tab === "role" ? "Role Breakdown" : tab === "fit" ? "CV Fit Map" : "Interview Prep"}
              </button>
            ))}
          </div>

          {activeTab === "role" && result.role_summary && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Card>
                <div style={{ fontWeight: 600, marginBottom: 10 }}>What this role actually is</div>
                <div style={{ fontSize: 14, lineHeight: 1.7 }}>{result.role_summary.actual_role}</div>
                <div style={{ display: "flex", gap: 12, marginTop: 12 }}>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    Seniority: <strong style={{ color: "var(--text)" }}>{result.role_summary.seniority}</strong>
                  </span>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
                    Remote: <strong style={{ color: result.role_summary.remote ? "var(--green)" : "var(--red)" }}>
                      {result.role_summary.remote ? "Yes" : "No"}
                    </strong>
                  </span>
                </div>
              </Card>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                <Card>
                  <div style={{ fontWeight: 600, marginBottom: 10, color: "var(--green)" }}>Must haves</div>
                  {(result.role_summary.key_requirements || []).map((r, i) => (
                    <div key={i} style={{ fontSize: 13, padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                      • {r}
                    </div>
                  ))}
                </Card>
                <Card>
                  <div style={{ fontWeight: 600, marginBottom: 10, color: "var(--amber)" }}>Nice to have</div>
                  {(result.role_summary.nice_to_have || []).map((r, i) => (
                    <div key={i} style={{ fontSize: 13, padding: "5px 0", borderBottom: "1px solid var(--border)" }}>
                      • {r}
                    </div>
                  ))}
                </Card>
              </div>

              {(result.role_summary.red_flags || []).length > 0 && (
                <Card style={{ borderColor: "var(--red)44" }}>
                  <div style={{ fontWeight: 600, marginBottom: 10, color: "var(--red)" }}>Red flags</div>
                  {result.role_summary.red_flags.map((r, i) => (
                    <div key={i} style={{ fontSize: 13, padding: "5px 0", color: "var(--red)" }}>⚠ {r}</div>
                  ))}
                </Card>
              )}
            </div>
          )}

          {activeTab === "fit" && result.fit_analysis && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Card style={{ borderColor: fitColor(result.fit_analysis.overall_fit) + "44" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                  <div style={{ fontWeight: 700, fontSize: 16, color: fitColor(result.fit_analysis.overall_fit) }}>
                    {result.fit_analysis.overall_fit?.toUpperCase()} FIT
                  </div>
                </div>
                <div style={{ fontSize: 13, lineHeight: 1.7, color: "var(--text-muted)" }}>
                  {result.fit_analysis.fit_summary}
                </div>
              </Card>

              <Card>
                <div style={{ fontWeight: 600, marginBottom: 12, color: "var(--green)" }}>
                  Where you match
                </div>
                {(result.fit_analysis.strong_matches || []).map((m, i) => (
                  <div key={i} style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: strengthColor(m.strength), fontWeight: 600 }}>
                        {m.strength}
                      </span>
                      <span style={{ fontWeight: 500, fontSize: 13 }}>{m.requirement}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
                      Evidence: {m.evidence}
                    </div>
                  </div>
                ))}
              </Card>

              {(result.fit_analysis.gaps || []).length > 0 && (
                <Card>
                  <div style={{ fontWeight: 600, marginBottom: 12, color: "var(--amber)" }}>
                    Gaps to address
                  </div>
                  {result.fit_analysis.gaps.map((g, i) => (
                    <div key={i} style={{ marginBottom: 14, paddingBottom: 14, borderBottom: "1px solid var(--border)" }}>
                      <div style={{ fontWeight: 500, fontSize: 13, color: "var(--amber)", marginBottom: 4 }}>
                        △ {g.requirement}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4 }}>
                        Gap: {g.gap}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--accent)" }}>
                        How to handle: {g.mitigation}
                      </div>
                    </div>
                  ))}
                </Card>
              )}
            </div>
          )}

          {activeTab === "questions" && result.interview_questions && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
              {[
                { key: "technical", label: "Technical Questions", color: "var(--accent)" },
                { key: "behavioral", label: "Behavioral Questions", color: "var(--green)" },
                { key: "role_specific", label: "Role-Specific Questions", color: "var(--amber)" },
              ].map(section => (
                <Card key={section.key}>
                  <div style={{ fontWeight: 600, color: section.color, marginBottom: 14 }}>
                    {section.label}
                  </div>
                  {((result.interview_questions as Record<string, { question: string; why_asked: string; your_answer_hint: string }[]>)[section.key] || []).map((q, i) => (
                    <div key={i} style={{
                      marginBottom: 16,
                      paddingBottom: 16,
                      borderBottom: "1px solid var(--border)",
                    }}>
                      <div style={{ fontWeight: 500, fontSize: 13, marginBottom: 4 }}>
                        {i + 1}. {q.question}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 6 }}>
                        Testing: {q.why_asked}
                      </div>
                      <div style={{ fontSize: 12, color: "var(--accent)", padding: "6px 10px", background: "var(--accent)11", borderRadius: 4 }}>
                        → {q.your_answer_hint}
                      </div>
                    </div>
                  ))}
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

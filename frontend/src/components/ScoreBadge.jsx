export default function ScoreBadge({ score }) {
  const pct = Math.round(score * 100);
  const tone =
    score >= 0.85 ? "text-verify bg-verify-soft" :
    score >= 0.7 ? "text-accent bg-accent-soft" :
    "text-muted bg-white/5";

  return (
    <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill font-mono text-sm font-medium ${tone}`}>
      <span>{pct}%</span>
      <span className="text-xs opacity-70 font-body">match</span>
    </div>
  );
}

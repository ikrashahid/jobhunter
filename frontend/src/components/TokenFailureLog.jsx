import { AlertTriangle, CheckCircle2 } from "lucide-react";

export default function TokenFailureLog({ truncatedCount, evaluatedCount }) {
  const hasTruncations = truncatedCount > 0;

  return (
    <div className="bg-surface border border-line rounded-card p-6">
      <div className="flex items-center gap-2 mb-1">
        <AlertTriangle size={16} className={hasTruncations ? "text-flag" : "text-verify"} />
        <h3 className="font-display font-semibold text-ink">Token guard</h3>
      </div>
      <p className="text-muted text-xs font-body mb-4">
        Job descriptions truncated before drafting to stay under Groq's per-request limit.
      </p>

      {evaluatedCount === 0 ? (
        <p className="text-muted text-sm font-body italic">No drafts evaluated yet.</p>
      ) : hasTruncations ? (
        <div className="flex items-center gap-2 text-flag">
          <span className="font-display font-semibold text-2xl">{truncatedCount}</span>
          <span className="text-sm font-body text-muted">
            of {evaluatedCount} drafts had their job description truncated
          </span>
        </div>
      ) : (
        <div className="flex items-center gap-2 text-verify">
          <CheckCircle2 size={18} />
          <span className="text-sm font-body">
            No truncations across {evaluatedCount} drafts — all descriptions fit comfortably.
          </span>
        </div>
      )}
    </div>
  );
}

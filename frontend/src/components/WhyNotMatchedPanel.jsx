import { HelpCircle } from "lucide-react";

const REASON_LABELS = {
  selected: { label: "selected", tone: "text-verify bg-verify-soft" },
  thin_description: { label: "description too short to embed well", tone: "text-flag bg-flag-soft" },
  rrf_ranked_below_top20: { label: "vector + keyword ranking too weak", tone: "text-muted bg-white/5" },
  cross_encoder_ranked_below_top5: { label: "re-ranked, but not in the top 5", tone: "text-accent bg-accent-soft" },
};

export default function WhyNotMatchedPanel({ reasonBreakdown }) {
  const total = reasonBreakdown.reduce((sum, r) => sum + r.count, 0);

  return (
    <div className="bg-surface border border-line rounded-card p-6">
      <div className="flex items-center gap-2 mb-1">
        <HelpCircle size={16} className="text-signal" />
        <h3 className="font-display font-semibold text-ink">Why didn't these match?</h3>
      </div>
      <p className="text-muted text-xs font-body mb-4">
        Every posting considered in the last scoring run, broken down by outcome.
      </p>

      {total === 0 ? (
        <p className="text-muted text-sm font-body italic">
          No match_log data yet — run the pipeline to populate this.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {reasonBreakdown.map((r) => {
            const meta = REASON_LABELS[r.reason] || { label: r.reason, tone: "text-muted bg-white/5" };
            const pct = Math.round((r.count / total) * 100);
            return (
              <div key={r.reason} className="flex items-center gap-3">
                <span className={`text-xs font-medium font-body px-2.5 py-1 rounded-pill whitespace-nowrap ${meta.tone}`}>
                  {meta.label}
                </span>
                <div className="flex-1 h-2 bg-white/5 rounded-pill overflow-hidden">
                  <div
                    className="h-full bg-signal/50 rounded-pill"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-ink text-sm font-mono w-16 text-right">
                  {r.count} <span className="text-muted text-xs">({pct}%)</span>
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

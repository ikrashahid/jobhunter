const VARIANTS = {
  drafted: { label: "drafted", cls: "bg-signal-soft text-signal" },
  notDrafted: { label: "not drafted yet", cls: "bg-white/5 text-muted" },
  checksOut: { label: "checks out", cls: "bg-verify-soft text-verify" },
  needsLook: { label: "needs a look", cls: "bg-flag-soft text-flag" },
};

export default function StatusPill({ variant }) {
  const v = VARIANTS[variant];
  if (!v) return null;
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-pill text-xs font-medium ${v.cls}`}>
      {v.label}
    </span>
  );
}

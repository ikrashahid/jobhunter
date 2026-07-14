import { useEffect, useState } from "react";
import { motion } from "framer-motion";

function AnimatedNumber({ value, suffix = "", decimals = 0 }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    let frame;
    const duration = 900;
    const start = performance.now();

    function tick(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(value * eased);
      if (progress < 1) frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return (
    <span>
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}

export default function StatsOverview({ matches }) {
  const total = matches.length;
  const drafted = matches.filter((m) => !!m.draft).length;
  const avgScore = total
    ? (matches.reduce((sum, m) => sum + m.score, 0) / total) * 100
    : 0;
  const flagged = matches.filter(
    (m) => m.eval && m.eval.faithfulness_score < 0.8
  ).length;

  const stats = [
    { label: "total matches", value: total, decimals: 0, suffix: "", color: "text-ink" },
    { label: "drafted", value: drafted, decimals: 0, suffix: "", color: "text-signal" },
    { label: "avg. match score", value: avgScore, decimals: 0, suffix: "%", color: "text-accent" },
    { label: "need a look", value: flagged, decimals: 0, suffix: "", color: "text-flag" },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
      {stats.map((s, i) => (
        <motion.div
          key={s.label}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.08, duration: 0.5, ease: "easeOut" }}
          className="relative bg-surface border border-line rounded-card p-5 overflow-hidden group
                     hover:border-signal/40 transition-colors duration-300"
        >
          <div className="absolute inset-0 bg-radial-glow opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          <p className={`relative font-display font-semibold text-3xl ${s.color}`}>
            <AnimatedNumber value={s.value} decimals={s.decimals} suffix={s.suffix} />
          </p>
          <p className="relative text-muted text-xs font-body mt-1">{s.label}</p>
        </motion.div>
      ))}
    </div>
  );
}

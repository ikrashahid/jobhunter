import { motion } from "framer-motion";

export default function StatCard({ label, value, tone = "text-ink", index = 0, sublabel }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.5 }}
      className="bg-surface border border-line rounded-card p-5"
    >
      <p className={`font-display font-semibold text-3xl ${tone}`}>{value}</p>
      <p className="text-muted text-xs font-body mt-1">{label}</p>
      {sublabel && <p className="text-muted/70 text-xs font-body mt-0.5">{sublabel}</p>}
    </motion.div>
  );
}

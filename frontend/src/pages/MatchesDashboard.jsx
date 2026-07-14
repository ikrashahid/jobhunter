import { useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Loader2, AlertCircle } from "lucide-react";
import MatchCard from "../components/MatchCard";
import StatsOverview from "../components/StatsOverview";
import { useMatches } from "../hooks/useMatches";

export default function MatchesDashboard({ onOpenMatch }) {
  const [filter, setFilter] = useState("all");
  const { data: matches, isLoading, isError, error } = useMatches();

  const all = matches ?? [];
  const filtered = all.filter((m) => {
    if (filter === "drafted") return !!m.draft;
    if (filter === "notDrafted") return !m.draft;
    return true;
  });

  return (
    <div className="flex-1 px-8 py-12 md:px-14 md:py-16 max-w-4xl">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center gap-2 text-accent mb-2"
      >
        <Sparkles size={18} />
        <span className="text-sm font-medium font-body">job hunter</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05 }}
        className="font-display font-semibold text-4xl text-ink mb-2"
      >
        Your best matches
      </motion.h1>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="text-muted font-body mb-8"
      >
        Sorted by relevance. Every draft below has been checked for accuracy before you see it.
      </motion.p>

      {!isLoading && !isError && <StatsOverview matches={all} />}

      <div className="flex items-center gap-2 mb-6">
        {[
          { key: "all", label: "all" },
          { key: "drafted", label: "drafted" },
          { key: "notDrafted", label: "not drafted" },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-4 py-1.5 rounded-pill text-sm font-medium font-body transition-all duration-200
              ${filter === f.key
                ? "bg-signal text-void shadow-glowSignal"
                : "bg-surface text-muted hover:text-ink border border-line"}`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="bg-surface border border-line rounded-card p-10 text-center flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-signal" size={22} />
          <p className="text-muted font-body text-sm">Loading your matches…</p>
        </div>
      )}

      {isError && (
        <div className="bg-surface border border-line rounded-card p-10 text-center flex flex-col items-center gap-2">
          <AlertCircle className="text-flag" size={22} />
          <p className="font-display text-ink font-medium">Couldn't load matches</p>
          <p className="text-muted font-body text-sm">{error?.message ?? "Check your Supabase connection."}</p>
        </div>
      )}

      {!isLoading && !isError && (
        <div className="flex flex-col gap-4">
          {filtered.length > 0 ? (
            filtered.map((match, i) => (
              <MatchCard key={match.id} match={match} index={i} onOpen={onOpenMatch} />
            ))
          ) : (
            <div className="bg-surface border border-line rounded-card p-10 text-center">
              <p className="font-display text-ink font-medium mb-1">Nothing here yet</p>
              <p className="text-muted font-body text-sm">
                Run the drafting pipeline to see matches appear.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { motion } from "framer-motion";
import { Activity, Loader2, AlertCircle } from "lucide-react";
import StatCard from "../components/StatCard";
import ScoreDistributionChart from "../components/ScoreDistributionChart";
import SourceBreakdownChart from "../components/SourceBreakdownChart";
import WhyNotMatchedPanel from "../components/WhyNotMatchedPanel";
import TokenFailureLog from "../components/TokenFailureLog";
import { usePipelineStats } from "../hooks/usePipelineStats";

export default function PipelineOverview() {
  const { data: stats, isLoading, isError, error } = usePipelineStats();

  return (
    <div className="flex-1 px-8 py-12 md:px-14 md:py-16 max-w-5xl">
      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex items-center gap-2 text-accent mb-2"
      >
        <Activity size={18} />
        <span className="text-sm font-medium font-body">pipeline health</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05 }}
        className="font-display font-semibold text-4xl text-ink mb-2"
      >
        What's actually happening
      </motion.h1>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="text-muted font-body mb-8"
      >
        The full picture — what got fetched, embedded, scored, and drafted, and why the rest didn't make it.
      </motion.p>

      {isLoading && (
        <div className="bg-surface border border-line rounded-card p-10 text-center flex flex-col items-center gap-3">
          <Loader2 className="animate-spin text-signal" size={22} />
          <p className="text-muted font-body text-sm">Loading pipeline stats…</p>
        </div>
      )}

      {isError && (
        <div className="bg-surface border border-line rounded-card p-10 text-center flex flex-col items-center gap-2">
          <AlertCircle className="text-flag" size={22} />
          <p className="font-display text-ink font-medium">Couldn't load pipeline stats</p>
          <p className="text-muted font-body text-sm">{error?.message ?? "Check your Supabase connection."}</p>
        </div>
      )}

      {stats && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <StatCard index={0} label="total postings" value={stats.totalPostings} />
            <StatCard index={1} label="embedded" value={stats.embeddedCount} tone="text-signal" />
            <StatCard index={2} label="scored" value={stats.scoredCount} tone="text-accent" />
            <StatCard index={3} label="drafted" value={stats.draftedCount} tone="text-verify" />
            <StatCard
              index={4}
              label="coverage"
              value={stats.coveragePct !== null ? `${stats.coveragePct}%` : "—"}
              tone="text-ink"
              sublabel={stats.thinCount ? `${stats.thinCount} too thin to embed well` : undefined}
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <StatCard
              index={5}
              label="avg. faithfulness"
              value={stats.avgFaithfulness !== null ? stats.avgFaithfulness.toFixed(2) : "—"}
              tone="text-verify"
            />
            <StatCard
              index={6}
              label="avg. quality"
              value={stats.avgQuality !== null ? stats.avgQuality.toFixed(2) : "—"}
              tone="text-signal"
            />
            <StatCard
              index={7}
              label="drafts truncated"
              value={stats.truncatedCount}
              tone={stats.truncatedCount > 0 ? "text-flag" : "text-verify"}
            />
            <StatCard
              index={8}
              label="drafts evaluated"
              value={stats.evaluatedCount}
              tone="text-ink"
            />
          </div>

          <div className="grid md:grid-cols-2 gap-5 mb-5">
            <ScoreDistributionChart data={stats.scoreDistribution} />
            <SourceBreakdownChart data={stats.sourceBreakdown} />
          </div>

          <div className="grid md:grid-cols-2 gap-5">
            <WhyNotMatchedPanel reasonBreakdown={stats.reasonBreakdown} />
            <TokenFailureLog
              truncatedCount={stats.truncatedCount}
              evaluatedCount={stats.evaluatedCount}
            />
          </div>
        </>
      )}
    </div>
  );
}

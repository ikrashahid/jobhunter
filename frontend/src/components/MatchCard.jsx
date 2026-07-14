import { motion } from "framer-motion";
import { Building2, ChevronRight, CheckCircle2, XCircle } from "lucide-react";
import ScoreBadge from "./ScoreBadge";
import StatusPill from "./StatusPill";

const cardVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.07, duration: 0.5, ease: [0.22, 1, 0.36, 1] },
  }),
};

export default function MatchCard({ match, index = 0, onOpen }) {
  const { posting, score, draft, eval: evalData } = match;
  const isDrafted = !!draft;

  const faithfulnessOk = evalData && evalData.faithfulness_score >= 0.8;
  const qualityOk = evalData && evalData.quality_score >= 0.8;

  const unsupportedCount = evalData
    ? evalData.verdicts.filter((v) => v.verdict === "UNSUPPORTED").length
    : 0;
  const supportedCount = evalData
    ? evalData.verdicts.filter((v) => v.verdict === "SUPPORTED").length
    : 0;

  const glow = isDrafted
    ? faithfulnessOk
      ? "hover:shadow-glowVerify"
      : "hover:shadow-glowFlag"
    : "hover:shadow-glowSignal";

  return (
    <motion.button
      custom={index}
      variants={cardVariants}
      initial="hidden"
      whileInView="visible"
      viewport={{ once: true, margin: "-40px" }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      whileTap={{ scale: 0.99 }}
      onClick={() => onOpen(match)}
      className={`w-full text-left bg-surface border border-line rounded-card
                 shadow-soft ${glow} transition-shadow duration-300
                 p-6 flex flex-col gap-4 group`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h3 className="font-display font-semibold text-lg text-ink leading-snug">
            {posting.title}
          </h3>
          <div className="flex items-center gap-1.5 text-muted text-sm font-body">
            <Building2 size={14} />
            <span>{posting.company}</span>
          </div>
        </div>
        <ScoreBadge score={score} />
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <StatusPill variant={isDrafted ? "drafted" : "notDrafted"} />
        {isDrafted && evalData && (
          <>
            <StatusPill variant={faithfulnessOk ? "checksOut" : "needsLook"} />
            {!qualityOk && (
              <span className="text-xs text-muted font-body italic">
                a phrase or two to clean up
              </span>
            )}
          </>
        )}
      </div>

      {isDrafted && evalData && (
        <div className="flex items-center gap-3 pt-3 border-t border-line">
          <div className="flex items-center gap-1 text-sm font-body text-verify">
            <CheckCircle2 size={15} />
            <span>{supportedCount} supported</span>
          </div>
          {unsupportedCount > 0 && (
            <div className="flex items-center gap-1 text-sm font-body text-flag">
              <XCircle size={15} />
              <span>{unsupportedCount} flagged</span>
            </div>
          )}
        </div>
      )}

      <div className="flex items-center justify-end text-signal text-sm font-medium font-body
                      opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <span>view details</span>
        <ChevronRight size={16} />
      </div>
    </motion.button>
  );
}

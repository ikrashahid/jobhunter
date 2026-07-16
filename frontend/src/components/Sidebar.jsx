import { motion } from "framer-motion";
import { LayoutGrid, FileText, User, Sparkles, Activity } from "lucide-react";

const NAV_ITEMS = [
  { key: "pipeline", label: "Pipeline", icon: Activity },
  { key: "dashboard", label: "Matches", icon: LayoutGrid },
  { key: "drafts", label: "Drafts", icon: FileText },
  { key: "profile", label: "Resume", icon: User },
];

export default function Sidebar({ active = "dashboard", onNavigate }) {
  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 flex flex-col gap-1 px-4 py-8
                       border-r border-line bg-void/60 backdrop-blur-sm">
      <div className="flex items-center gap-2 px-3 mb-10">
        <motion.div
          animate={{ rotate: [0, 15, -10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        >
          <Sparkles className="text-accent" size={20} />
        </motion.div>
        <span className="font-display font-semibold text-ink text-lg">job hunter</span>
      </div>

      {NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const isActive = active === item.key;
        return (
          <button
            key={item.key}
            onClick={() => onNavigate?.(item.key)}
            className="relative px-3 py-2.5 rounded-xl flex items-center gap-3 text-sm font-body font-medium
                       transition-colors duration-200 group"
          >
            {isActive && (
              <motion.div
                layoutId="nav-active-bg"
                className="absolute inset-0 bg-signal-soft rounded-xl"
                transition={{ type: "spring", bounce: 0.25, duration: 0.5 }}
              />
            )}
            <Icon
              size={17}
              className={`relative z-10 transition-colors duration-200
                ${isActive ? "text-signal" : "text-muted group-hover:text-ink"}`}
            />
            <span
              className={`relative z-10 transition-colors duration-200
                ${isActive ? "text-signal" : "text-muted group-hover:text-ink"}`}
            >
              {item.label}
            </span>
          </button>
        );
      })}
    </aside>
  );
}

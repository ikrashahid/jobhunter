"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/matches", label: "Matches" },
  { href: "/analyze", label: "Analyze JD" },
  { href: "/metrics", label: "Metrics" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav style={{
      borderBottom: "1px solid var(--border)",
      background: "var(--surface)",
      padding: "0 24px",
      display: "flex",
      alignItems: "center",
      gap: 8,
      height: 52,
    }}>
      <span style={{ fontWeight: 700, color: "var(--accent)", marginRight: 24, fontSize: 15 }}>
        Job Copilot
      </span>
      {links.map(l => (
        <Link key={l.href} href={l.href} style={{
          padding: "6px 12px",
          borderRadius: 6,
          color: path === l.href ? "var(--accent)" : "var(--text-muted)",
          background: path === l.href ? "var(--surface2)" : "transparent",
          textDecoration: "none",
          fontSize: 13,
          fontWeight: path === l.href ? 600 : 400,
        }}>
          {l.label}
        </Link>
      ))}
    </nav>
  );
}

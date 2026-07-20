"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import styles from "./login.module.css";

type Phase = "campus" | "walk" | "bus" | "desk" | "click" | "form";

const PHASE_MS: { phase: Phase; at: number }[] = [
  { phase: "campus", at: 0 },
  { phase: "walk", at: 1600 },
  { phase: "bus", at: 4200 },
  { phase: "desk", at: 7000 },
  { phase: "click", at: 9800 },
  { phase: "form", at: 11200 },
];

export default function LoginPage() {
  const router = useRouter();
  const [phase, setPhase] = useState<Phase>("campus");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    if (mq.matches) {
      setPhase("form");
      return;
    }

    const timers = PHASE_MS.slice(1).map(({ phase: p, at }) =>
      window.setTimeout(() => setPhase(p), at)
    );
    return () => timers.forEach(clearTimeout);
  }, []);

  function skipToForm() {
    setPhase("form");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.error || "Invalid credentials");
        return;
      }
      router.replace("/");
      router.refresh();
    } catch {
      setError("Could not reach the login service");
    } finally {
      setSubmitting(false);
    }
  }

  const showForm = phase === "form" || reducedMotion;

  return (
    <div className={`${styles.stage} ${styles[`phase_${phase}`]}`}>
      <div className={styles.sky} aria-hidden />
      <div className={styles.ground} aria-hidden />

      <div className={styles.campusLayer} aria-hidden>
        <University />
        <Graduate walking={phase === "walk" || phase === "bus"} />
      </div>

      <div className={styles.busLayer} aria-hidden>
        <svg className={styles.route} viewBox="0 0 900 80" preserveAspectRatio="none">
          <path
            d="M40 48 Q 220 10, 400 48 T 760 48 T 880 40"
            className={styles.routePath}
          />
          <circle cx="40" cy="48" r="5" className={styles.routeDot} />
          <circle cx="880" cy="40" r="5" className={styles.routeDot} />
          <text x="40" y="72" className={styles.routeLabel}>
            Campus
          </text>
          <text x="820" y="72" className={styles.routeLabel}>
            Home
          </text>
        </svg>
        <Bus />
      </div>

      <div className={styles.deskLayer} aria-hidden>
        <DeskScene clicking={phase === "click" || phase === "form"} />
      </div>

      <div className={`${styles.formWrap} ${showForm ? styles.formVisible : ""}`}>
        <div className={styles.glass}>
          <p className={styles.brand}>Jobhunter</p>
          <h1 className={styles.headline}>Welcome home.</h1>
          <p className={styles.sub}>
            From graduation to the hunt — sign in to review matches worth sending.
          </p>

          <form className={styles.form} onSubmit={onSubmit}>
            <label className={styles.label}>
              Username
              <input
                className={styles.input}
                name="username"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </label>
            <label className={styles.label}>
              Password
              <input
                className={styles.input}
                name="password"
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {error && <p className={styles.error}>{error}</p>}
            <button className={styles.submit} type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Enter Jobhunter"}
            </button>
          </form>
        </div>
      </div>

      {!showForm && (
        <button type="button" className={styles.skip} onClick={skipToForm}>
          Skip intro
        </button>
      )}

      <p className={styles.caption} aria-live="polite">
        {phase === "campus" && "Campus morning…"}
        {phase === "walk" && "Diploma in hand."}
        {phase === "bus" && "Route home."}
        {phase === "desk" && "Searching for the next role…"}
        {phase === "click" && "Opening Jobhunter."}
        {phase === "form" && ""}
      </p>
    </div>
  );
}

function University() {
  return (
    <svg className={styles.uni} viewBox="0 0 160 140" role="img" aria-label="University">
      <rect x="20" y="48" width="120" height="72" rx="2" fill="#2a3340" />
      <rect x="28" y="56" width="18" height="22" fill="#7dd3c7" opacity="0.55" />
      <rect x="54" y="56" width="18" height="22" fill="#7dd3c7" opacity="0.45" />
      <rect x="80" y="56" width="18" height="22" fill="#7dd3c7" opacity="0.55" />
      <rect x="106" y="56" width="18" height="22" fill="#7dd3c7" opacity="0.4" />
      <rect x="28" y="86" width="18" height="22" fill="#7dd3c7" opacity="0.35" />
      <rect x="54" y="86" width="18" height="22" fill="#7dd3c7" opacity="0.5" />
      <rect x="106" y="86" width="18" height="22" fill="#7dd3c7" opacity="0.4" />
      <rect x="72" y="92" width="16" height="28" fill="#1a222c" />
      <polygon points="80,8 18,48 142,48" fill="#3d4a5c" />
      <rect x="74" y="18" width="12" height="22" fill="#c4a35a" />
      <circle cx="80" cy="16" r="5" fill="#e8c56a" />
      <rect x="0" y="118" width="160" height="8" fill="#1e2a24" />
    </svg>
  );
}

function Graduate({ walking }: { walking: boolean }) {
  return (
    <div className={`${styles.graduate} ${walking ? styles.graduateWalk : ""}`}>
      <svg viewBox="0 0 64 96" className={styles.graduateSvg}>
        <polygon points="32,6 8,16 32,20 56,16" fill="#1a1a1a" />
        <rect x="28" y="16" width="8" height="6" fill="#1a1a1a" />
        <line x1="48" y1="14" x2="58" y2="28" stroke="#c4a35a" strokeWidth="1.5" />
        <circle cx="58" cy="30" r="2.5" fill="#c4a35a" />
        <path
          d="M18 28 Q32 18 46 28 Q48 42 44 48 Q32 44 20 48 Q16 40 18 28Z"
          fill="#c23b2e"
        />
        <ellipse cx="32" cy="38" rx="11" ry="13" fill="#e8b896" />
        <ellipse cx="27" cy="37" rx="2.2" ry="2.6" fill="#8a6b3d" />
        <ellipse cx="37" cy="37" rx="2.2" ry="2.6" fill="#8a6b3d" />
        <circle cx="27.5" cy="36.5" r="0.7" fill="#fff" />
        <circle cx="37.5" cy="36.5" r="0.7" fill="#fff" />
        <path d="M28 44 Q32 47 36 44" fill="none" stroke="#c47a6a" strokeWidth="1.2" />
        <path d="M18 52 Q32 48 46 52 L50 88 Q32 94 14 88 Z" fill="#1c1c22" />
        <path d="M24 52 L32 70 L40 52" fill="#2a2a32" opacity="0.5" />
        <g className={styles.diploma}>
          <rect
            x="46"
            y="58"
            width="14"
            height="10"
            rx="1"
            fill="#f3e9d2"
            transform="rotate(-18 53 63)"
          />
          <rect
            x="48"
            y="60"
            width="10"
            height="1"
            fill="#c4a35a"
            transform="rotate(-18 53 63)"
          />
        </g>
        <rect x="24" y="86" width="5" height="10" fill="#1a1a1a" className={styles.legL} />
        <rect x="35" y="86" width="5" height="10" fill="#1a1a1a" className={styles.legR} />
      </svg>
    </div>
  );
}

function Bus() {
  return (
    <div className={styles.bus}>
      <svg viewBox="0 0 88 40" className={styles.busSvg}>
        <rect x="4" y="8" width="76" height="22" rx="4" fill="#2f6f6a" />
        <rect x="10" y="12" width="14" height="10" rx="1" fill="#b8e8e0" />
        <rect x="28" y="12" width="14" height="10" rx="1" fill="#b8e8e0" />
        <rect x="46" y="12" width="14" height="10" rx="1" fill="#b8e8e0" />
        <rect x="64" y="12" width="12" height="10" rx="1" fill="#93d5cb" />
        <circle cx="20" cy="32" r="5" fill="#1a1a1a" />
        <circle cx="64" cy="32" r="5" fill="#1a1a1a" />
        <circle cx="20" cy="32" r="2" fill="#888" />
        <circle cx="64" cy="32" r="2" fill="#888" />
        <circle cx="35" cy="16" r="3" fill="#e8b896" />
        <path d="M31 14 Q35 10 39 14" fill="#c23b2e" />
      </svg>
    </div>
  );
}

function DeskScene({ clicking }: { clicking: boolean }) {
  return (
    <div className={styles.desk}>
      <svg viewBox="0 0 320 220" className={styles.deskSvg}>
        <rect width="320" height="220" fill="transparent" />
        <rect x="40" y="150" width="240" height="14" rx="2" fill="#3a2f28" />
        <rect x="56" y="164" width="12" height="36" fill="#2a221c" />
        <rect x="252" y="164" width="12" height="36" fill="#2a221c" />
        <rect
          x="100"
          y="70"
          width="120"
          height="78"
          rx="4"
          fill="#1a1f28"
          stroke="#4a5568"
          strokeWidth="3"
        />
        <rect x="108" y="78" width="104" height="58" fill="#0d1218" />
        <rect x="114" y="84" width="60" height="6" rx="1" fill="#3d4a5c" />
        <rect x="114" y="94" width="90" height="5" rx="1" fill="#2a3340" />
        <rect x="114" y="104" width="80" height="5" rx="1" fill="#2a3340" />
        <rect
          x="130"
          y="116"
          width="60"
          height="14"
          rx="3"
          className={clicking ? styles.jhBtnActive : styles.jhBtn}
        />
        <text x="160" y="126" textAnchor="middle" className={styles.jhBtnText}>
          Jobhunter
        </text>
        <polygon
          points="188,118 188,132 193,128 198,136 201,135 194,126 200,124"
          className={`${styles.cursor} ${clicking ? styles.cursorClick : ""}`}
          fill="#e8e8e8"
        />
        <g transform="translate(210, 95)">
          <path
            d="M8 28 Q20 8 32 28 Q34 48 28 58 Q20 52 12 58 Q6 44 8 28Z"
            fill="#c23b2e"
          />
          <ellipse cx="20" cy="36" rx="10" ry="12" fill="#e8b896" />
          <ellipse cx="16" cy="35" rx="1.8" ry="2.2" fill="#8a6b3d" />
          <ellipse cx="24" cy="35" rx="1.8" ry="2.2" fill="#8a6b3d" />
          <path d="M16 42 Q20 45 24 42" fill="none" stroke="#c47a6a" strokeWidth="1" />
          <path d="M4 58 Q20 52 36 58 L38 90 L2 90 Z" fill="#2c4a52" />
          <path
            d="M8 68 Q0 78 20 82"
            fill="none"
            stroke="#e8b896"
            strokeWidth="4"
            strokeLinecap="round"
          />
          <path
            d="M32 68 Q48 76 40 82"
            fill="none"
            stroke="#e8b896"
            strokeWidth="4"
            strokeLinecap="round"
          />
        </g>
        <rect x="120" y="142" width="70" height="8" rx="2" fill="#2a2a32" />
      </svg>
    </div>
  );
}

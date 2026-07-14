/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Dark canvas
        void: "#0D0B1A",         // page background, near-black indigo
        surface: "#161329",      // card background
        surfaceHi: "#1F1B38",    // hovered/elevated card
        line: "#2A2545",         // hairline borders on dark

        ink: "#F3F1FB",          // primary text on dark
        muted: "#9691B8",        // secondary text on dark

        signal: {
          DEFAULT: "#8B96FF",    // brighter periwinkle for dark bg
          soft: "rgba(139,150,255,0.14)",
          glow: "rgba(139,150,255,0.45)",
        },
        verify: {
          DEFAULT: "#5FE0AE",
          soft: "rgba(95,224,174,0.14)",
          glow: "rgba(95,224,174,0.40)",
        },
        flag: {
          DEFAULT: "#FF8A72",
          soft: "rgba(255,138,114,0.14)",
          glow: "rgba(255,138,114,0.40)",
        },
        accent: {
          DEFAULT: "#FFD166",
          soft: "rgba(255,209,102,0.14)",
          glow: "rgba(255,209,102,0.40)",
        },
      },
      fontFamily: {
        display: ["Fredoka", "sans-serif"],
        body: ["Plus Jakarta Sans", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
      borderRadius: {
        card: "20px",
        pill: "999px",
      },
      boxShadow: {
        soft: "0 2px 20px rgba(0,0,0,0.35)",
        lift: "0 12px 40px rgba(0,0,0,0.5)",
        glowSignal: "0 0 0 1px rgba(139,150,255,0.35), 0 8px 32px rgba(139,150,255,0.25)",
        glowVerify: "0 0 0 1px rgba(95,224,174,0.35), 0 8px 32px rgba(95,224,174,0.20)",
        glowFlag: "0 0 0 1px rgba(255,138,114,0.35), 0 8px 32px rgba(255,138,114,0.20)",
      },
      backgroundImage: {
        "radial-glow": "radial-gradient(circle at 20% 0%, rgba(139,150,255,0.12), transparent 40%), radial-gradient(circle at 80% 20%, rgba(255,209,102,0.08), transparent 40%)",
      },
    },
  },
  plugins: [],
};

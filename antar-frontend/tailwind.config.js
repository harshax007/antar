/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        void: "var(--void)",
        surface: "var(--surface)",
        cyan: { DEFAULT: "var(--cyan)" },
        amber: "var(--amber)",
        red: "var(--red)",
        green: "var(--green)",
        ink: "var(--text)",
        muted: "var(--muted)",
        "accent-ink": "var(--accent-ink)",
        "field-bg": "var(--field-bg)"
      },
      fontFamily: {
        display: ['"Chakra Petch"', "ui-sans-serif", "sans-serif"],
        body: ["Inter", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
        kn: ['"Noto Sans Kannada"', "sans-serif"],
      },
      borderRadius: { card: "12px", pill: "999px" },
      boxShadow: {
        "glow-cyan": "0 0 24px rgba(34,230,240,.35), 0 0 60px rgba(34,230,240,.12)",
        "glow-green": "0 0 24px rgba(24,214,154,.4)",
        card: "0 24px 70px rgba(0,0,0,.55), inset 0 1px 0 rgba(255,255,255,.06)",
      },
    },
  },
  plugins: [],
};

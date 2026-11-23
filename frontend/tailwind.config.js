/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        stadium: {
          darkest: "#06090e",
          bg: "#090d15",
          surface: "#0f1523",
          card: "#141c2e",
          border: "#1f2b45",
          highlight: "#2a3b5c",
        },
        cyan: {
          neon: "#00f0ff",
          glow: "#38bdf8",
        },
        violet: {
          neon: "#8b5cf6",
          deep: "#6d28d9",
        },
        pitch: {
          line: "rgba(16, 185, 129, 0.25)",
          grass: "#062817",
          border: "#059669",
        },
        gold: {
          trophy: "#f59e0b",
          glow: "#fbbf24",
        },
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "sans-serif"],
        display: ["Space Grotesk", "Chakra Petch", "sans-serif"],
        mono: ["JetBrains Mono", "Courier New", "monospace"],
      },
      boxShadow: {
        "cyan-glow": "0 0 20px rgba(0, 240, 255, 0.35)",
        "cyan-glow-lg": "0 0 35px rgba(0, 240, 255, 0.5)",
        "violet-glow": "0 0 20px rgba(139, 92, 246, 0.35)",
        "gold-glow": "0 0 25px rgba(245, 158, 11, 0.4)",
        "stadium-card": "0 10px 30px -10px rgba(0, 0, 0, 0.7)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "float": "float 4s ease-in-out infinite",
        "shimmer": "shimmer 2.5s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};

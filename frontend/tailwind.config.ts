import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#0f172a",
        foreground: "#f1f5f9",
        card: "#1e293b",
        accent: "#3b82f6",
        muted: "#334155",
        "muted-foreground": "#94a3b8",
        border: "#334155",
      },
    },
  },
  plugins: [],
};
export default config;

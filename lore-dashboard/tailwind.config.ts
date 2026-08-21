import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        panel: "#f7f8fa",
        line: "#d9dee7",
        teal: "#0f766e",
        amber: "#b45309",
        rose: "#be123c"
      }
    }
  },
  plugins: []
};

export default config;

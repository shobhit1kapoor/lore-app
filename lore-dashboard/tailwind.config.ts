import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#f4f4f5",
        panel: "#171717",
        line: "#303030",
        teal: "#2dd4bf",
        amber: "#fbbf24",
        rose: "#fb7185"
      }
    }
  },
  plugins: []
};

export default config;

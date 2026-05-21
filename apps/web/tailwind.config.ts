import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "sans-serif"],
      },
      colors: {
        ink: "#17201b",
        moss: "#2f5d50",
        mint: "#d9f2e6",
        coral: "#ef6f61",
        cloud: "#f6f8f4",
        line: "#dce5dc",
      },
      boxShadow: {
        soft: "0 18px 50px rgba(23, 32, 27, 0.10)",
      },
    },
  },
  plugins: [],
};

export default config;

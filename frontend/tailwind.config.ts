import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: "#8F8F8E",
        // Slightly darker brand grey: keeps white text at AA contrast on hover.
        "brand-soft": "#6B6B6A",
        ink: "#2B2B2A",
        muted: "#6B6B6A",
        action: "#2B2B2A",
        surface: "#FAFAF9",
        subtle: "#F5F5F4",
        line: "#E5E5E3",
        gray: {
          50: "#FAFAF9",
          100: "#F5F5F4",
          200: "#E5E5E3",
          300: "#C5C5C3",
          400: "#8F8F8E",
          500: "#6B6B6A",
          600: "#595958",
          700: "#454544",
          800: "#2B2B2A",
          900: "#20201F",
        },
        // ─── LEGACY ALIASES ────────────────────────────────────────────────
        // The old warm bakery palette (cream / coral / mocha) was replaced by
        // the neutral logo palette. These aliases keep the ~1,000 remaining
        // legacy class usages visually correct while files are migrated one
        // by one. REMOVE THIS BLOCK once `grep -r "mocha|pink-pastel|cream"`
        // returns zero matches across src/.
        mocha: "#2B2B2A", // was #5C3D2E (brown)  -> ink
        "pink-pastel": "#2B2B2A", // was #E8837A (coral)  -> action
        cream: "#FAFAF9", // was #FDF6EE (cream)  -> surface
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      fontFamily: {
        heading: ["var(--font-playfair)", "serif"],
        body: ["var(--font-dm-sans)", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;

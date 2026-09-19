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
        // ─── Bảng màu lấy từ thiết kế Stitch ──────────────────────────────
        // Trích trực tiếp bằng cách đọc pixel ảnh thiết kế, không ước lượng:
        //   nền #FAF8F5 · nền phụ #F3EFE9 · mực #1F1B1A
        //   khối CTA #2B2625 · vàng nhấn #FEDEB2 / #FAB361
        //
        // Tông kem ấm thay cho xám trung tính: màu kem gợi giấy, bơ và kem
        // tươi — đúng chất tiệm bánh — trong khi xám trung tính đọc ra như
        // giao diện phần mềm.
        brand: "#90908F", // màu logo, vẫn dùng cho chi tiết phụ
        "brand-soft": "#6B6B6A",
        ink: "#1F1B1A",
        muted: "#6B6560", // xám ngả nâu cho hợp nền kem
        action: "#1F1B1A",
        surface: "#FAF8F5", // nền chính
        subtle: "#F3EFE9", // nền phụ
        line: "#E8E3DC", // đường kẻ ngả kem
        // Vàng nhấn: dùng cho nút nổi bật trên nền tối và nhãn "đặc biệt".
        gold: "#FEDEB2",
        "gold-deep": "#FAB361",
        // Khối tối (CTA, footer tối)
        cocoa: "#2B2625",
        gray: {
          50: "#FAF8F5",
          100: "#F3EFE9",
          200: "#E8E3DC",
          300: "#CFC8C0",
          400: "#90908F",
          500: "#6B6560",
          600: "#595350",
          700: "#403A38",
          800: "#2B2625",
          900: "#1F1B1A",
        },
        // ─── LEGACY ALIASES ────────────────────────────────────────────────
        // The old warm bakery palette (cream / coral / mocha) was replaced by
        // the neutral logo palette. These aliases keep the ~1,000 remaining
        // legacy class usages visually correct while files are migrated one
        // by one. REMOVE THIS BLOCK once `grep -r "mocha|pink-pastel|cream"`
        // returns zero matches across src/.
        mocha: "#1F1B1A", // was #5C3D2E (brown)  -> ink
        "pink-pastel": "#1F1B1A", // was #E8837A (coral)  -> action
        cream: "#FAF8F5", // was #FDF6EE (cream)  -> surface
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      fontFamily: {
        heading: ["var(--font-playfair)", "Georgia", "serif"],
        // Be Vietnam Pro thay cho DM Sans: DM Sans không có subset tiếng Việt
        // trên Google Fonts, khiến chữ có dấu bị vỡ nét.
        body: ["var(--font-body)", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;

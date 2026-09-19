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
        // Màu lấy CHÍNH XÁC từ file logo (frontend/public/brand/bo-no-logo.png).
        // Logo chỉ có MỘT màu duy nhất #90908F trên 3.473.403 pixel — đã phân
        // tích bằng script, không ước lượng bằng mắt.
        brand: "#90908F",
        // Xám đậm hơn cho hover: giữ chữ trắng đạt tương phản AA (5.3:1).
        // Không dùng #90908F làm nền nút vì chữ trắng chỉ đạt 2.7:1.
        "brand-soft": "#6B6B6A",
        // ─── Tông "sang trọng": đen mực ấm, không dùng đen tuyền ──────────
        // Đen tuyền #000 trông gắt và rẻ tiền; các thương hiệu cao cấp dùng
        // đen ngả nâu/xám rất nhẹ để mềm mắt mà vẫn sâu.
        ink: "#1F1E1D",
        muted: "#6B6B6A",
        action: "#1F1E1D",
        // Nền trắng ngà thay vì trắng tinh — ánh giấy, ấm và cao cấp hơn.
        surface: "#FBFAF8",
        subtle: "#F4F3F1",
        line: "#E3E2DF",
        // Đường viền mảnh kim loại cho chi tiết trang trí.
        gold: "#B8A88A",
        gray: {
          50: "#FBFAF8",
          100: "#F4F3F1",
          200: "#E3E2DF",
          300: "#C5C5C3",
          400: "#90908F",
          500: "#6B6B6A",
          600: "#595958",
          700: "#454544",
          800: "#1F1E1D",
          900: "#171716",
        },
        // ─── LEGACY ALIASES ────────────────────────────────────────────────
        // The old warm bakery palette (cream / coral / mocha) was replaced by
        // the neutral logo palette. These aliases keep the ~1,000 remaining
        // legacy class usages visually correct while files are migrated one
        // by one. REMOVE THIS BLOCK once `grep -r "mocha|pink-pastel|cream"`
        // returns zero matches across src/.
        mocha: "#1F1E1D", // was #5C3D2E (brown)  -> ink
        "pink-pastel": "#1F1E1D", // was #E8837A (coral)  -> action
        cream: "#FBFAF8", // was #FDF6EE (cream)  -> surface
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

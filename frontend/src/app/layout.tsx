import type { Metadata, Viewport } from "next";
import { Playfair_Display, Be_Vietnam_Pro } from "next/font/google";
import dynamic from "next/dynamic";
import { AuthProvider } from "@/contexts/AuthContext";
import { CartProvider } from "@/contexts/CartContext";
import { LoyaltyProvider } from "@/contexts/LoyaltyContext";
import RoleBoundary from "@/components/RoleBoundary";
import "./globals.css";

// ---- Fonts ----
// Playfair Display: tiêu đề serif. Google Fonts có subset "vietnamese" cho
// font này nên dấu tiếng Việt hiển thị đúng.
const playfair = Playfair_Display({
  subsets: ["latin", "vietnamese"],
  variable: "--font-playfair",
  display: "swap",
});

/**
 * Be Vietnam Pro cho phần thân.
 *
 * Trước đây dùng DM Sans, nhưng DM Sans KHÔNG có subset "vietnamese" trên
 * Google Fonts — chỉ có latin và latin-ext. Hệ quả: mọi ký tự có dấu như
 * "THIẾT KẾ BÁNH" rơi vào font dự phòng của hệ điều hành, nên nét chữ vỡ và
 * lệch hẳn khỏi phần chữ không dấu đứng cạnh. Đã kiểm tra bằng cách đọc
 * unicode-range trong CSS của Google Fonts, không đoán.
 *
 * Be Vietnam Pro được thiết kế riêng cho tiếng Việt, có đủ 5 thanh và dấu
 * mũ, đồng thời vẫn là sans-serif hình học nên đi với Playfair rất hợp.
 */
const beVietnam = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

// ---- Dynamic import: ChatWidget loads AFTER page is interactive ----
// This keeps the initial JS bundle small (ChatWidget is ~10KB+ with SSE logic)
const ChatWidget = dynamic(() => import("@/components/ChatWidget"), {
  ssr: false, // Chat is fully client-side
  loading: () => null, // No flash while loading
});

// ---- SEO Metadata ----
export const metadata: Metadata = {
  title: {
    template: "%s | Bơ Nơ – Tiệm Bánh Kem",
    default: "Bơ Nơ – Tiệm Bánh Kem Thủ Công Đà Nẵng",
  },
  description:
    "Tiệm bánh kem tùy chỉnh tại Đà Nẵng – Thiết kế bánh kem theo ý muốn với công cụ trực quan và AI tư vấn thông minh bằng tiếng Việt.",
  keywords: ["bánh kem", "cake shop", "tiệm bánh", "thiết kế bánh", "Đà Nẵng"],
  authors: [{ name: "Bơ Nơ Bakery" }],
  openGraph: {
    type: "website",
    locale: "vi_VN",
    siteName: "Bơ Nơ",
    title: "Bơ Nơ – Tiệm Bánh Kem Thủ Công Đà Nẵng",
    description:
      "Thiết kế bánh kem theo ý muốn với công cụ trực quan và AI tư vấn thông minh.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

// ---- Viewport config (prevents double-tap zoom on mobile) ----
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5, // Allow user zoom (accessibility)
  // Thanh trạng thái trên điện thoại — màu nâu đậm của khối CTA, đồng bộ với
  // tông kem. Phải dùng mã màu trực tiếp, KHÔNG dùng var(--brand-cocoa): thẻ
  // meta theme-color được trình duyệt đọc trước khi CSS chạy, nên biến CSS sẽ
  // không phân giải được và thanh trạng thái mất màu.
  themeColor: "#2B2625",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`${playfair.variable} ${beVietnam.variable}`} suppressHydrationWarning>
      <head>
        {/* Preconnect to Google Fonts CDN (already loaded by next/font but good practice) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-body antialiased">
        <AuthProvider>
          <CartProvider>
            <LoyaltyProvider>
              <RoleBoundary>
                {children}
                {/* ChatWidget loaded dynamically to not block initial paint */}
                <ChatWidget />
              </RoleBoundary>
            </LoyaltyProvider>
          </CartProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

import type { Metadata, Viewport } from "next";
import { Playfair_Display, DM_Sans } from "next/font/google";
import dynamic from "next/dynamic";
import { AuthProvider } from "@/contexts/AuthContext";
import { CartProvider } from "@/contexts/CartContext";
import "./globals.css";

// ---- Fonts ----
const playfair = Playfair_Display({
  subsets: ["latin", "vietnamese"],
  variable: "--font-playfair",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin", "latin-ext"],
  variable: "--font-dm-sans",
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
    default: "Bơ Nơ – Tiệm Bánh Kem Thủ Công TP.HCM",
  },
  description:
    "Tiệm bánh kem tùy chỉnh tại TP.HCM – Thiết kế bánh kem theo ý muốn với công cụ trực quan và AI tư vấn thông minh bằng tiếng Việt.",
  keywords: ["bánh kem", "cake shop", "tiệm bánh", "thiết kế bánh", "TP.HCM"],
  authors: [{ name: "Bơ Nơ Bakery" }],
  openGraph: {
    type: "website",
    locale: "vi_VN",
    siteName: "Bơ Nơ",
    title: "Bơ Nơ – Tiệm Bánh Kem Thủ Công TP.HCM",
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
  themeColor: "#e8837a",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`${playfair.variable} ${dmSans.variable}`}>
      <head>
        {/* Preconnect to Google Fonts CDN (already loaded by next/font but good practice) */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-body antialiased">
        <AuthProvider>
          <CartProvider>
            {children}
            {/* ChatWidget loaded dynamically to not block initial paint */}
            <ChatWidget />
          </CartProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

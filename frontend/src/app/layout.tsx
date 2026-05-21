import type { Metadata } from "next";
import { Playfair_Display, DM_Sans } from "next/font/google";
import ChatWidget from "@/components/ChatWidget";
import "./globals.css";

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

export const metadata: Metadata = {
  title: "Tiệm Bánh Kem | Cake Shop",
  description:
    "Tiệm bánh kem tùy chỉnh tại TP.HCM - Thiết kế bánh kem theo ý muốn với AI tư vấn",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi" className={`${playfair.variable} ${dmSans.variable}`}>
      <body className="font-body antialiased">
        {children}
        <ChatWidget />
      </body>
    </html>
  );
}

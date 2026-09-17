import type { Metadata } from "next";
import Link from "next/link";
import Header from "@/components/Header";
import BrandLogo from "@/components/BrandLogo";

export const metadata: Metadata = {
  title: "Trang chủ",
  description:
    "Bơ Nơ Bakery – Thiết kế bánh kem theo ý muốn với công cụ trực quan 3D và AI tư vấn thông minh bằng tiếng Việt tại TP.HCM.",
};

export default function Home() {
  return (
    <main className="min-h-screen bg-surface">
      {/* Navigation */}
      <Header />

      {/* Hero Section */}
      <section
        className="page-container pt-12 pb-8 sm:pt-16 sm:pb-12 text-center"
        aria-labelledby="hero-heading"
      >
        <h1
          id="hero-heading"
          className="hero-title font-heading text-ink font-bold mb-4"
        >
          Tiệm Bánh Kem
        </h1>
        <p className="font-heading text-2xl sm:text-[32px] text-ink mb-6">
          Bơ Nơ Bakery
        </p>
        <p className="text-lg sm:text-xl leading-relaxed text-muted font-body max-w-[760px] mx-auto mb-8">
          Thiết kế bánh kem theo ý muốn với công cụ trực quan và AI tư vấn thông minh.
          Mỗi chiếc bánh là một tác phẩm nghệ thuật dành riêng cho bạn.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/cake-builder"
            className="btn btn-primary"
          >
            Thiết kế bánh ngay
          </Link>
          <Link
            href="/products"
            className="btn btn-secondary"
          >
            Xem menu bánh
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section
        className="page-container pt-8 pb-12 sm:pb-16"
        aria-labelledby="features-heading"
      >
        <h2
          id="features-heading"
          className="font-heading text-3xl sm:text-4xl leading-tight text-ink font-bold text-center mb-8"
        >
          Tại sao chọn Bơ Nơ Bakery?
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Feature 1 */}
          <article className="feature-card">
            <FeatureIcon type="design" />
            <h3 className="font-heading text-2xl text-ink font-bold mb-4">
              Click-to-Customize
            </h3>
            <p className="text-muted font-body text-base leading-relaxed">
              Thiết kế bánh kem trực quan bằng SVG. Chọn màu, topping, trang trí — thấy kết quả ngay lập tức.
            </p>
          </article>

          {/* Feature 2 */}
          <article className="feature-card">
            <FeatureIcon type="chat" />
            <h3 className="font-heading text-2xl text-ink font-bold mb-4">
              AI Tư Vấn
            </h3>
            <p className="text-muted font-body text-base leading-relaxed">
              Chatbot AI giúp bạn chọn bánh phù hợp theo dịp, số người, ngân sách. Tư vấn bằng tiếng Việt.
            </p>
          </article>

          {/* Feature 3 */}
          <article className="feature-card sm:col-span-2 lg:col-span-1">
            <FeatureIcon type="order" />
            <h3 className="font-heading text-2xl text-ink font-bold mb-4">
              Đặt hàng dễ dàng
            </h3>
            <p className="text-muted font-body text-base leading-relaxed">
              Chọn ngày nhận, xác nhận đơn hàng, theo dõi trạng thái — tất cả trên một nền tảng.
            </p>
          </article>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-white border-y border-line py-12 sm:py-16" aria-labelledby="cta-heading">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2
            id="cta-heading"
            className="font-heading text-3xl sm:text-4xl text-ink font-bold mb-4"
          >
            Sẵn sàng tạo chiếc bánh của bạn?
          </h2>
          <p className="text-muted font-body mb-8 text-lg">
            Bắt đầu thiết kế ngay hoặc nhờ AI tư vấn — chỉ cần click nút chat ở góc phải.
          </p>
          <Link
            href="/cake-builder"
            className="btn btn-primary"
          >
            Bắt đầu thiết kế
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white py-8 sm:py-12">
        <div className="page-container flex flex-col items-center gap-6 text-center font-body text-base">
          <Link href="/" aria-label="Bơ Nơ Bakery — Trang chủ"><BrandLogo /></Link>
          <div>
            <p className="mb-2 text-ink">Bơ Nơ Bakery — Tiệm Bánh Kem Thủ Công</p>
            <p className="text-muted">TP. Đà Nẵng | ☎ 0901 234 567</p>
          </div>
        </div>
      </footer>
    </main>
  );
}

function FeatureIcon({ type }: { type: "design" | "chat" | "order" }) {
  return (
    <svg className="mx-auto mb-6 h-12 w-12 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {type === "design" && <><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" /><path d="m4 7.5 8 4.5 8-4.5M12 12v9M8 5.25l8 4.5" /></>}
      {type === "chat" && <><path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H6l-4 3V11.5A7.5 7.5 0 0 1 9.5 4H14" /><path d="m19 2 1 3 3 1-3 1-1 3-1-3-3-1 3-1 1-3Z" /><path d="M7 11h7M7 15h4" /></>}
      {type === "order" && <><rect x="4" y="6" width="16" height="15" rx="2" /><path d="M8 6V4a4 4 0 0 1 8 0v2M9 13l2 2 4-4" /></>}
    </svg>
  );
}

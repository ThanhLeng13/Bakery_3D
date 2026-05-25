import type { Metadata } from "next";
import Link from "next/link";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "Trang chủ",
  description:
    "La Douceur – Thiết kế bánh kem theo ý muốn với công cụ trực quan 3D và AI tư vấn thông minh bằng tiếng Việt tại TP.HCM.",
};

export default function Home() {
  return (
    <main className="min-h-screen bg-cream">
      {/* Navigation */}
      <Header />

      {/* Hero Section */}
      <section
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16 md:py-24 text-center"
        aria-labelledby="hero-heading"
      >
        <h1
          id="hero-heading"
          className="font-heading text-3xl sm:text-4xl md:text-6xl text-mocha font-bold mb-3 sm:mb-4 animate-fade-in"
        >
          Tiệm Bánh Kem
        </h1>
        <p className="font-heading text-xl sm:text-2xl md:text-3xl text-pink-pastel mb-4 sm:mb-6 animate-fade-in animate-delay-100">
          La Douceur
        </p>
        <p className="text-base sm:text-lg md:text-xl text-mocha/70 font-body max-w-2xl mx-auto mb-8 sm:mb-10 animate-fade-in animate-delay-200">
          Thiết kế bánh kem theo ý muốn với công cụ trực quan và AI tư vấn thông minh.
          Mỗi chiếc bánh là một tác phẩm nghệ thuật dành riêng cho bạn.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center animate-fade-in animate-delay-300">
          <Link
            href="/cake-builder"
            className="px-6 sm:px-8 py-3 sm:py-4 bg-pink-pastel text-white font-body font-semibold text-base sm:text-lg rounded-full hover:bg-pink-pastel/90 hover:shadow-lg transition-all min-h-[44px] flex items-center justify-center"
          >
            ✨ Thiết kế bánh ngay
          </Link>
          <Link
            href="/products"
            className="px-6 sm:px-8 py-3 sm:py-4 bg-white text-mocha font-body font-semibold text-base sm:text-lg rounded-full border-2 border-mocha/20 hover:border-pink-pastel hover:text-pink-pastel transition-all min-h-[44px] flex items-center justify-center"
          >
            Xem menu bánh
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section
        className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16"
        aria-labelledby="features-heading"
      >
        <h2
          id="features-heading"
          className="font-heading text-2xl sm:text-3xl text-mocha font-bold text-center mb-8 sm:mb-12"
        >
          Tại sao chọn La Douceur?
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-5 sm:gap-8">
          {/* Feature 1 */}
          <article className="bg-white rounded-2xl p-5 sm:p-6 shadow-sm text-center hover:shadow-md transition-shadow">
            <div className="text-3xl sm:text-4xl mb-3 sm:mb-4" aria-hidden="true">🎨</div>
            <h3 className="font-heading text-base sm:text-lg text-mocha font-bold mb-2">
              Click-to-Customize
            </h3>
            <p className="text-mocha/70 font-body text-sm">
              Thiết kế bánh kem trực quan bằng SVG. Chọn màu, topping, trang trí — thấy kết quả ngay lập tức.
            </p>
          </article>

          {/* Feature 2 */}
          <article className="bg-white rounded-2xl p-5 sm:p-6 shadow-sm text-center hover:shadow-md transition-shadow">
            <div className="text-3xl sm:text-4xl mb-3 sm:mb-4" aria-hidden="true">🤖</div>
            <h3 className="font-heading text-base sm:text-lg text-mocha font-bold mb-2">
              AI Tư Vấn
            </h3>
            <p className="text-mocha/70 font-body text-sm">
              Chatbot AI giúp bạn chọn bánh phù hợp theo dịp, số người, ngân sách. Tư vấn bằng tiếng Việt.
            </p>
          </article>

          {/* Feature 3 */}
          <article className="bg-white rounded-2xl p-5 sm:p-6 shadow-sm text-center hover:shadow-md transition-shadow sm:col-span-2 md:col-span-1">
            <div className="text-3xl sm:text-4xl mb-3 sm:mb-4" aria-hidden="true">📦</div>
            <h3 className="font-heading text-base sm:text-lg text-mocha font-bold mb-2">
              Đặt hàng dễ dàng
            </h3>
            <p className="text-mocha/70 font-body text-sm">
              Chọn ngày nhận, xác nhận đơn hàng, theo dõi trạng thái — tất cả trên một nền tảng.
            </p>
          </article>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-white py-12 sm:py-16" aria-labelledby="cta-heading">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2
            id="cta-heading"
            className="font-heading text-2xl sm:text-3xl text-mocha font-bold mb-3 sm:mb-4"
          >
            Sẵn sàng tạo chiếc bánh của bạn?
          </h2>
          <p className="text-mocha/70 font-body mb-6 sm:mb-8 text-sm sm:text-base">
            Bắt đầu thiết kế ngay hoặc nhờ AI tư vấn — chỉ cần click nút chat ở góc phải.
          </p>
          <Link
            href="/cake-builder"
            className="inline-flex items-center justify-center px-6 sm:px-8 py-3 sm:py-4 bg-pink-pastel text-white font-body font-semibold text-base sm:text-lg rounded-full hover:bg-pink-pastel/90 hover:shadow-lg transition-all min-h-[44px]"
          >
            Bắt đầu thiết kế
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-mocha text-white/80 py-6 sm:py-8">
        <div className="max-w-7xl mx-auto px-4 text-center font-body text-xs sm:text-sm">
          <p className="mb-1 sm:mb-2">🎂 La Douceur — Tiệm Bánh Kem Thủ Công</p>
          <p className="text-white/50">TP. Hồ Chí Minh | ☎ 0901 234 567</p>
        </div>
      </footer>
    </main>
  );
}

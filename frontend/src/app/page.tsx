import Link from "next/link";
import Header from "@/components/Header";

export default function Home() {
  return (
    <main className="min-h-screen bg-cream">
      {/* Navigation */}
      <Header />

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-4 py-16 md:py-24 text-center">
        <h1 className="font-heading text-4xl md:text-6xl text-mocha font-bold mb-4">
          Tiệm Bánh Kem
        </h1>
        <h2 className="font-heading text-2xl md:text-3xl text-pink-pastel mb-6">
          La Douceur
        </h2>
        <p className="text-lg md:text-xl text-mocha/70 font-body max-w-2xl mx-auto mb-10">
          Thiết kế bánh kem theo ý muốn với công cụ trực quan và AI tư vấn thông minh.
          Mỗi chiếc bánh là một tác phẩm nghệ thuật dành riêng cho bạn.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link
            href="/cake-builder"
            className="px-8 py-4 bg-pink-pastel text-white font-body font-semibold text-lg rounded-full hover:bg-pink-pastel/90 hover:shadow-lg transition-all min-h-[44px]"
          >
            ✨ Thiết kế bánh ngay
          </Link>
          <Link
            href="/products"
            className="px-8 py-4 bg-white text-mocha font-body font-semibold text-lg rounded-full border-2 border-mocha/20 hover:border-pink-pastel hover:text-pink-pastel transition-all min-h-[44px]"
          >
            Xem menu bánh
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto px-4 py-16">
        <h3 className="font-heading text-2xl md:text-3xl text-mocha font-bold text-center mb-12">
          Tại sao chọn La Douceur?
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Feature 1 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
            <div className="text-4xl mb-4">🎨</div>
            <h4 className="font-heading text-lg text-mocha font-bold mb-2">
              Click-to-Customize
            </h4>
            <p className="text-mocha/70 font-body text-sm">
              Thiết kế bánh kem trực quan bằng SVG. Chọn màu, topping, trang trí — thấy kết quả ngay lập tức.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
            <div className="text-4xl mb-4">🤖</div>
            <h4 className="font-heading text-lg text-mocha font-bold mb-2">
              AI Tư Vấn
            </h4>
            <p className="text-mocha/70 font-body text-sm">
              Chatbot AI giúp bạn chọn bánh phù hợp theo dịp, số người, ngân sách. Tư vấn bằng tiếng Việt.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="bg-white rounded-2xl p-6 shadow-sm text-center">
            <div className="text-4xl mb-4">📦</div>
            <h4 className="font-heading text-lg text-mocha font-bold mb-2">
              Đặt hàng dễ dàng
            </h4>
            <p className="text-mocha/70 font-body text-sm">
              Chọn ngày nhận, xác nhận đơn hàng, theo dõi trạng thái — tất cả trên một nền tảng.
            </p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-white py-16">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <h3 className="font-heading text-2xl md:text-3xl text-mocha font-bold mb-4">
            Sẵn sàng tạo chiếc bánh của bạn?
          </h3>
          <p className="text-mocha/70 font-body mb-8">
            Bắt đầu thiết kế ngay hoặc nhờ AI tư vấn — chỉ cần click nút chat ở góc phải.
          </p>
          <Link
            href="/cake-builder"
            className="inline-block px-8 py-4 bg-pink-pastel text-white font-body font-semibold text-lg rounded-full hover:bg-pink-pastel/90 hover:shadow-lg transition-all min-h-[44px]"
          >
            Bắt đầu thiết kế
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-mocha text-white/80 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center font-body text-sm">
          <p className="mb-2">🎂 La Douceur — Tiệm Bánh Kem Thủ Công</p>
          <p className="text-white/50">TP. Hồ Chí Minh | ☎ 0901 234 567</p>
        </div>
      </footer>
    </main>
  );
}

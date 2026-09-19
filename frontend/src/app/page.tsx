import type { Metadata } from "next";
import Link from "next/link";
import Header from "@/components/Header";
import BrandLogo from "@/components/BrandLogo";

export const metadata: Metadata = {
  title: "Bơ Nơ Bakery – Bánh kem thủ công",
  description:
    "Bơ Nơ Bakery – Bánh kem thủ công thiết kế theo yêu cầu, xem trước bằng mô hình 3D và tư vấn bằng AI tiếng Việt.",
};

/**
 * Icon nét mảnh dùng chung.
 *
 * Vẽ bằng SVG thay vì emoji hay icon font: emoji render khác nhau trên mỗi hệ
 * điều hành, còn icon font buộc tải thêm một file. Nét 1.25 mảnh hơn nét 2
 * thông thường — ở cỡ lớn, nét mảnh trông tinh tế hơn hẳn nét dày.
 */
function ThinIcon({ path }: { path: string }) {
  return (
    <svg
      className="h-10 w-10 text-brand"
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.25"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

const FEATURES = [
  {
    n: "01",
    title: "Thiết kế trực quan",
    body: "Chọn màu, topping và trang trí, xem trước chiếc bánh của bạn ngay trên trình duyệt.",
    path: "M24 6l16 9v18l-16 9-16-9V15z M24 24l16-9 M24 24v18 M24 24L8 15",
  },
  {
    n: "02",
    title: "Tư vấn bằng AI",
    body: "Trò chuyện tự nhiên để tìm mẫu bánh hợp dịp, số người và ngân sách của bạn.",
    path: "M8 12a4 4 0 014-4h24a4 4 0 014 4v16a4 4 0 01-4 4H20l-8 8v-8h-4z",
  },
  {
    n: "03",
    title: "Tìm bánh bằng ảnh",
    body: "Tải lên ảnh chiếc bánh bạn thích, hệ thống tìm ra mẫu gần giống nhất trong tiệm.",
    path: "M6 12a2 2 0 012-2h32a2 2 0 012 2v24a2 2 0 01-2 2H8a2 2 0 01-2-2z M6 32l10-9 8 7 6-5 12 11 M17 19a3 3 0 100-6 3 3 0 000 6z",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-surface">
      <Header />

      {/* ─── Hero ──────────────────────────────────────────────────────────
          Chữ nhỏ hơn và nhẹ hơn so với landing page thông thường: thương hiệu
          cao cấp dùng typography tiết chế và để khoảng trắng nói thay. Tiêu đề
          64px đậm 700 là ngôn ngữ của trang bán hàng, không phải của tiệm bánh
          thủ công. Ở đây tối đa 56px và độ đậm 500. */}
      <section
        className="page-container pt-20 pb-24 sm:pt-28 sm:pb-32 text-center"
        aria-labelledby="hero-heading"
      >
        <p className="eyebrow mb-6">Thủ công · TP.HCM</p>

        <h1
          id="hero-heading"
          className="title-lux text-[2.25rem] leading-[1.1] sm:text-[3rem] md:text-[3.5rem] text-ink mb-7"
        >
          Bánh kem
          <br />
          <span className="italic">làm riêng cho bạn</span>
        </h1>

        <hr className="rule-fade max-w-[200px] mx-auto mb-7" />

        <p className="text-base sm:text-lg leading-[1.75] text-muted max-w-[540px] mx-auto mb-11">
          Mỗi chiếc bánh được thiết kế theo yêu cầu, xem trước bằng mô hình 3D
          trước khi đặt. Bạn chọn — chúng tôi làm.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link href="/cake-builder" className="btn btn-primary w-full sm:w-auto">
            Thiết kế bánh
          </Link>
          <Link href="/products" className="btn btn-secondary w-full sm:w-auto">
            Xem menu
          </Link>
        </div>
      </section>

      {/* ─── Dải phân cách ─────────────────────────────────────────────────
          Chữ kẹp giữa hai đường kẻ mảnh: thủ pháp của tạp chí in, tạo nhịp nghỉ
          giữa hai khối lớn mà không cần thêm màu hay hình ảnh. */}
      <div className="page-container">
        <div className="flex items-center gap-6 sm:gap-10">
          <hr className="rule-fade flex-1" />
          <p className="eyebrow whitespace-nowrap">Vì sao chọn Bơ Nơ</p>
          <hr className="rule-fade flex-1" />
        </div>
      </div>

      {/* ─── Ba điểm chính ─────────────────────────────────────────────────
          Đánh số 01/02/03 thay vì ba thẻ giống hệt nhau. Ba khối vuông vức
          cạnh nhau là dấu hiệu của template; số thứ tự gợi cảm giác một bộ
          sưu tập được tuyển chọn. Các khối ngăn bằng đường kẻ 1px thay vì
          khoảng trống, để chúng đọc như một dải liền mạch. */}
      <section
        className="page-container pt-16 pb-24 sm:pb-32"
        aria-label="Điểm nổi bật"
      >
        <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-3 border-y border-line">
          {FEATURES.map((f) => (
            <article
              key={f.n}
              className="bg-surface px-8 py-12 sm:px-10 sm:py-14 transition-colors duration-500 hover:bg-white"
            >
              <p className="font-heading text-sm text-brand mb-7 tracking-[0.2em]">
                {f.n}
              </p>
              <ThinIcon path={f.path} />
              <h3 className="mt-7 mb-3 font-heading text-xl text-ink font-normal">
                {f.title}
              </h3>
              <p className="text-muted text-[0.9375rem] leading-[1.7]">
                {f.body}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* ─── Lời mời cuối ──────────────────────────────────────────────────── */}
      <section className="page-container pb-24 sm:pb-32 text-center">
        <hr className="rule-fade max-w-[120px] mx-auto mb-12" />
        <h2 className="title-lux text-2xl sm:text-[2rem] text-ink mb-5 max-w-[520px] mx-auto">
          Sẵn sàng cho chiếc bánh của riêng bạn?
        </h2>
        <p className="text-muted text-base leading-[1.75] max-w-[440px] mx-auto mb-10">
          Bắt đầu thiết kế, hoặc hỏi trợ lý AI nếu bạn chưa biết chọn gì.
        </p>
        <Link href="/cake-builder" className="btn btn-primary">
          Bắt đầu thiết kế
        </Link>
      </section>

      {/* ─── Footer ────────────────────────────────────────────────────────── */}
      <footer className="border-t border-line py-14">
        <div className="page-container flex flex-col items-center gap-6 text-center">
          <Link href="/" aria-label="Bơ Nơ Bakery — Trang chủ">
            <BrandLogo />
          </Link>
          <hr className="rule-fade max-w-[80px]" />
          <p className="text-muted text-sm leading-relaxed">
            Bơ Nơ Bakery — Tiệm bánh kem thủ công
            <br />
            TP. Đà Nẵng · 0901 234 567
          </p>
        </div>
      </footer>
    </main>
  );
}

import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import Header from "@/components/Header";
import BrandLogo from "@/components/BrandLogo";
import NewsletterForm from "@/components/NewsletterForm";

export const metadata: Metadata = {
  title: "Bơ Nơ Bakery – Bánh kem nghệ thuật",
  description:
    "Bơ Nơ Bakery – Bánh kem thủ công thiết kế theo yêu cầu, xem trước bằng mô hình 3D và tư vấn bằng AI tiếng Việt.",
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ShowcaseProduct {
  url: string;
  name: string;
  price: number;
  tag: string;
}

/**
 * Lấy ảnh bánh thật cho trang chủ (hero + dải sản phẩm).
 *
 * Trả về mảng rỗng nếu API chưa chạy — trang chủ vẫn phải hiển thị được, chỉ
 * là ẩn các khối ảnh đi, chứ không được vỡ.
 */
async function getShowcase(): Promise<ShowcaseProduct[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/products?page_size=10`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    const out: ShowcaseProduct[] = [];
    for (const p of data.products ?? []) {
      if (p.image_url) {
        out.push({
          url: p.image_url,
          name: p.name,
          price: p.base_price,
          tag: "",
        });
      }
    }
    return out;
  } catch {
    return [];
  }
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(price);
}

/** Icon nét mảnh cho ba khối giá trị. */
function ValueIcon({ path }: { path: string }) {
  return (
    <svg
      className="h-9 w-9 text-ink"
      viewBox="0 0 40 40"
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

const VALUES = [
  {
    n: "01",
    title: "Trực quan hóa mô hình 3D",
    body: "Tự do xoay 360°, chỉnh tông màu kem, nắp và thử nghiệm nhân phủ trước khi duyệt làm.",
    cta: "Thử công cụ 3D ngay",
    href: "/cake-builder",
    path: "M20 5l13 7.5v15L20 35 7 27.5v-15z M20 20l13-7.5 M20 20v15 M20 20L7 12.5",
  },
  {
    n: "02",
    title: "Tư vấn thảo thuận cùng đầu bếp",
    body: "Đội ngũ nghệ nhân lắng nghe câu chuyện, phong cách tiếp và ngân sách để tạo nên bản phác thảo độc quyền.",
    cta: "Đặt lịch hẹn tư vấn",
    href: "/products",
    path: "M7 10a3 3 0 013-3h20a3 3 0 013 3v13a3 3 0 01-3 3H16l-6 6v-6H10a3 3 0 01-3-3z",
  },
  {
    n: "03",
    title: "Tái hiện hoàn hảo từ ảnh mẫu",
    body: "Tải lên bất kỳ ảnh bánh mẫu nào. Hệ thống phân tích và tìm ra mẫu bánh gần giống nhất trong tiệm.",
    cta: "Tải ảnh lên thử nghiệm",
    href: "/tim-banh",
    path: "M5 10a2 2 0 012-2h26a2 2 0 012 2v20a2 2 0 01-2 2H7a2 2 0 01-2-2z M5 27l8-7 7 6 5-4 10 9 M14 16a2.5 2.5 0 100-5 2.5 2.5 0 000 5z",
  },
];

export default async function Home() {
  const showcase = await getShowcase();
  const heroImage = showcase[0];
  const strip = showcase.slice(1, 5);

  return (
    <main className="min-h-screen bg-surface">
      <Header />

      {/* ─── Hero hai cột ──────────────────────────────────────────────────
          Chữ bên trái, ảnh bên phải. Bố cục hai cột cho phép ảnh bánh lớn —
          thứ quan trọng nhất với một tiệm bánh — mà không đẩy chữ xuống dưới
          màn hình như bố cục căn giữa. */}
      <section className="page-container pt-12 pb-20 sm:pt-16 sm:pb-28">
        <div className="grid items-center gap-12 lg:grid-cols-[1fr_minmax(0,480px)] lg:gap-16">
          {/* Cột chữ */}
          <div>
            {/* Nhãn: dấu chấm vàng + chữ in hoa giãn nhẹ, trên nền pill kem. */}
            <p className="inline-flex items-center gap-2 rounded-full bg-subtle px-3.5 py-1.5 text-[0.6875rem] font-medium uppercase tracking-[0.14em] text-muted mb-7">
              <span className="h-1.5 w-1.5 rounded-full bg-gold-deep" />
              Atelier thủ công · TP. Đà Nẵng
            </p>

            <h1 className="title-lux text-[2.5rem] leading-[1.05] sm:text-[3.25rem] lg:text-[3.5rem] text-ink mb-6">
              Bánh kem nghệ thuật
              <br />
              <span className="italic">làm riêng cho bạn</span>
            </h1>

            <p className="text-[0.9375rem] sm:text-base leading-[1.75] text-muted max-w-[520px] mb-9">
              Mỗi chiếc bánh là một tác phẩm độc bản được phác thảo theo câu
              chuyện riêng, phối hợp mô hình 3D chân thực 360° trước khi bắt đầu
              tạo hình. Bạn tưởng tượng — chúng tôi hiện thực.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 mb-10">
              <Link href="/cake-builder" className="btn btn-primary">
                Bắt đầu thiết kế 3D
              </Link>
              <Link href="/products" className="btn btn-secondary">
                Khám phá menu
              </Link>
            </div>

            {/* Ba điểm tin cậy, ngăn bằng đường kẻ dọc mảnh. */}
            <ul className="flex flex-col sm:flex-row gap-4 sm:gap-7 border-t border-line pt-6">
              {[
                "Mô hình 3D trực quan",
                "100% Bơ AOP & tài cây tươi",
                "Giao lạnh chuyên dụng 24/7",
              ].map((item, i) => (
                <li
                  key={item}
                  className={`flex items-start gap-2 text-[0.8125rem] leading-snug text-muted ${
                    i > 0 ? "sm:border-l sm:border-line sm:pl-7" : ""
                  }`}
                >
                  <svg
                    className="mt-0.5 h-4 w-4 shrink-0 text-ink"
                    viewBox="0 0 20 20"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    aria-hidden="true"
                  >
                    <circle cx="10" cy="10" r="7.5" />
                    <path d="M7 10l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Cột ảnh — khung vòm, thủ pháp của tạp chí thời trang. */}
          {heroImage && (
            <div className="relative">
              <div className="arch relative aspect-[4/5] w-full bg-subtle shadow-[0_24px_60px_-32px_rgba(31,27,26,0.35)]">
                <Image
                  src={heroImage.url}
                  alt={heroImage.name}
                  fill
                  sizes="(max-width: 1024px) 100vw, 480px"
                  className="object-cover"
                  priority
                />
                {/* Thẻ thông tin nhỏ nằm đè lên ảnh, lệch xuống dưới. */}
                <div className="absolute inset-x-4 bottom-4 flex items-end justify-between gap-3 rounded-2xl bg-surface/95 backdrop-blur-sm px-4 py-3">
                  <div>
                    <p className="text-[0.625rem] uppercase tracking-[0.14em] text-muted mb-1">
                      Haute pâtisserie collection
                    </p>
                    <p className="font-heading text-sm text-ink">
                      Mẫu thiết kế độc bản 2025
                    </p>
                  </div>
                  <Link
                    href="/products"
                    aria-label="Xem bộ sưu tập"
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-action text-surface transition-colors hover:bg-cocoa"
                  >
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 20 20"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      aria-hidden="true"
                    >
                      <path d="M5 15L15 5M9 5h6v6" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </Link>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ─── Ba giá trị ──────────────────────────────────────────────────── */}
      <section className="page-container pb-20 sm:pb-28" aria-labelledby="values-heading">
        <div className="text-center mb-12">
          <p className="eyebrow mb-3">Giá trị nghệ nhân</p>
          <h2
            id="values-heading"
            className="title-lux text-[1.75rem] sm:text-[2.25rem] text-ink"
          >
            Vì sao khách hàng chọn Bơ Nơ
          </h2>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {VALUES.map((v) => (
            <article
              key={v.n}
              className="flex flex-col rounded-2xl border border-line bg-white p-7 sm:p-8 transition-shadow duration-500 hover:shadow-[0_18px_44px_-28px_rgba(31,27,26,0.3)]"
            >
              <div className="flex items-start justify-between mb-7">
                <p className="font-heading text-sm italic text-muted">{v.n}</p>
                <ValueIcon path={v.path} />
              </div>
              <h3 className="font-heading text-lg text-ink mb-3 leading-snug">
                {v.title}
              </h3>
              <p className="text-sm leading-[1.7] text-muted flex-1">{v.body}</p>
              <Link
                href={v.href}
                className="link-underline mt-6 self-start text-[0.8125rem] text-ink"
              >
                {v.cta} →
              </Link>
            </article>
          ))}
        </div>
      </section>

      {/* ─── Dải sản phẩm ──────────────────────────────────────────────────── */}
      {strip.length > 0 && (
        <section className="page-container pb-20 sm:pb-28" aria-labelledby="strip-heading">
          <div className="text-center mb-12">
            <p className="eyebrow mb-3">Hương vị đặc trưng tại Bơ Nơ</p>
            <h2
              id="strip-heading"
              className="title-lux text-[1.75rem] sm:text-[2.25rem] text-ink max-w-[620px] mx-auto"
            >
              Dòng bánh tươi thủ công trong ngày
            </h2>
          </div>

          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {strip.map((item, i) => (
              <article
                key={item.url}
                className="flex flex-col rounded-2xl border border-line bg-white p-4 transition-shadow duration-500 hover:shadow-[0_18px_44px_-28px_rgba(31,27,26,0.3)]"
              >
                <div className="relative aspect-[4/3] w-full overflow-hidden rounded-xl bg-subtle mb-4">
                  <Image
                    src={item.url}
                    alt={item.name}
                    fill
                    sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 25vw"
                    className="object-cover"
                  />
                </div>
                {i === 0 && <span className="tag-gold mb-2 self-start">Thủ công</span>}
                <h3 className="font-heading text-base text-ink leading-snug line-clamp-2 mb-2">
                  {item.name}
                </h3>
                <div className="mt-auto flex items-center justify-between gap-3 pt-3">
                  <p className="text-sm text-ink tracking-wide">
                    {formatPrice(item.price)}
                  </p>
                  <Link
                    href="/products"
                    className="rounded-full bg-action px-4 py-1.5 text-[0.6875rem] font-medium uppercase tracking-[0.06em] text-surface transition-colors hover:bg-cocoa"
                  >
                    Đặt ngay
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* ─── Khối CTA nền nâu đậm ──────────────────────────────────────────── */}
      <section className="page-container pb-20 sm:pb-28">
        <div className="cta-cocoa px-6 py-16 sm:px-14 sm:py-20 text-center">
          <p className="eyebrow-light mb-5">Bespoke confectionery atelier</p>
          <h2 className="title-lux text-[1.75rem] leading-tight sm:text-[2.5rem] text-surface mb-5 max-w-[560px] mx-auto">
            Sẵn sàng sáng tạo chiếc
            <br />
            <span className="italic text-gold">bánh của riêng bạn?</span>
          </h2>
          <p className="text-sm sm:text-base leading-[1.75] text-surface/70 max-w-[480px] mx-auto mb-10">
            Bắt đầu với trợ lý thiết kế thông minh, hoặc gửi ảnh mẫu để đội ngũ
            thợ bánh Bơ Nơ liên hệ tư vấn ngay trong 15 phút.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link href="/cake-builder" className="btn-gold">
              Khởi tạo bản thiết kế
            </Link>
            <Link href="/tim-banh" className="btn-outline-light">
              Chat với bánh nghệ nhân
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Footer bốn cột ────────────────────────────────────────────────── */}
      <footer className="border-t border-line pt-16 pb-10">
        <div className="page-container">
          <div className="grid gap-10 lg:grid-cols-[1.2fr_1fr_1fr_1.2fr] lg:gap-12">
            {/* Cột 1: thương hiệu */}
            <div>
              <Link href="/" aria-label="Bơ Nơ Bakery — Trang chủ">
                <BrandLogo />
              </Link>
              <p className="mt-5 text-[0.8125rem] leading-relaxed text-muted max-w-[280px]">
                Tiệm bánh kem thủ công &amp; nghệ thuật bánh ngọt độc bản, kiến
                tạo khoảnh khắc ngọt ngào giữa đời thường.
              </p>
              <div className="flex gap-2 mt-5">
                {["IG", "FB", "TT"].map((s) => (
                  <span
                    key={s}
                    className="flex h-9 w-9 items-center justify-center rounded-full border border-line text-[0.6875rem] font-medium text-muted"
                    aria-hidden="true"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Cột 2 */}
            <div>
              <h3 className="text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-ink mb-5">
                Atelier &amp; tiệm bánh
              </h3>
              <div className="space-y-4 text-[0.8125rem] leading-relaxed text-muted">
                <p>
                  <span className="text-ink">Chi nhánh Đà Nẵng:</span>
                  <br />
                  45 Bạch Đằng, Quận Hải Châu, TP. Đà Nẵng
                </p>
                <p>
                  <span className="text-ink">Giờ mở cửa:</span> 08:00 – 21:30
                  hằng ngày
                </p>
              </div>
            </div>

            {/* Cột 3 */}
            <div>
              <h3 className="text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-ink mb-5">
                Chăm sóc khách hàng
              </h3>
              <div className="space-y-4 text-[0.8125rem] leading-relaxed text-muted">
                <p>
                  <span className="text-ink">Đặt bánh &amp; tư vấn:</span>
                  <br />
                  Liên hệ qua hotline hoặc fanpage của tiệm
                </p>
                <p>
                  <span className="text-ink">Nhận bánh tại:</span>
                  <br />
                  Chi nhánh Hải Châu, TP. Đà Nẵng
                </p>
              </div>
            </div>

            {/* Cột 4: đăng ký nhận tin */}
            <div>
              <h3 className="text-[0.6875rem] font-semibold uppercase tracking-[0.14em] text-ink mb-5">
                Nhận tin mới nhất
              </h3>
              <p className="text-[0.8125rem] leading-relaxed text-muted mb-4">
                Nhận ưu đãi độc quyền và bộ sưu tập mùa lễ hội từ Bơ Nơ Bakery.
              </p>
              {/* Form chưa nối API — chỉ để hoàn thiện giao diện, không giả vờ
                  là đã hoạt động. */}
              <NewsletterForm />
            </div>
          </div>

          {/* Dòng bản quyền */}
          <div className="mt-14 pt-6 border-t border-line flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between text-[0.75rem] text-muted">
            <p>© 2025 Bơ Nơ Bakery. All rights reserved.</p>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              <span>Chính sách bảo mật</span>
              <span>Điều khoản dịch vụ</span>
              <span>Chính sách giao hàng</span>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}

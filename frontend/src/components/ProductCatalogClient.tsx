"use client";

import { useTransition } from "react";
import { useRouter, usePathname } from "next/navigation";
import ProductCard from "./ProductCard";
import SkeletonCard from "./SkeletonCard";
import { ProductListItem } from "@/types";

type CategoryFilter = "all" | "bánh âu" | "bánh ngọt";

const CATEGORIES: { label: string; value: CategoryFilter }[] = [
  { label: "Tất cả", value: "all" },
  { label: "Bánh Âu", value: "bánh âu" },
  { label: "Bánh Ngọt", value: "bánh ngọt" },
];

interface ProductCatalogClientProps {
  initialProducts: ProductListItem[];
  initialTotalPages: number;
  currentPage: number;
  currentCategory: string;
}

export default function ProductCatalogClient({
  initialProducts,
  initialTotalPages,
  currentPage,
  currentCategory,
}: ProductCatalogClientProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isPending, startTransition] = useTransition();

  const handleFilterChange = (category: string, page: number) => {
    const params = new URLSearchParams();
    if (category !== "all") {
      params.set("category", category);
    }
    if (page > 1) {
      params.set("page", page.toString());
    }

    startTransition(() => {
      router.push(`${pathname}?${params.toString()}`);
    });
  };

  return (
    <main className="min-h-screen bg-surface">
      {/* ─── Tiêu đề ───────────────────────────────────────────────────────
          Bỏ thanh nền trắng đổ bóng: một dải màu khác chạy ngang màn hình là
          ngôn ngữ của bảng điều khiển. Tiệm bánh cao cấp để tiêu đề nằm trực
          tiếp trên nền giấy, ngăn cách bằng một đường kẻ mảnh. */}
      <div className="page-container pt-14 pb-10 sm:pt-20 sm:pb-14 text-center">
        <p className="eyebrow mb-5">Bộ sưu tập</p>
        <h1 className="title-lux text-[1.875rem] sm:text-[2.5rem] text-ink mb-5">
          Danh mục bánh kem
        </h1>
        <hr className="rule-fade max-w-[160px] mx-auto mb-6" />
        <p className="text-muted text-base max-w-[480px] mx-auto leading-relaxed">
          Bánh kem thủ công, làm theo yêu cầu cho từng dịp.
        </p>
      </div>

      <div className="page-container pb-20">
        {/* ─── Bộ lọc ──────────────────────────────────────────────────────
            Kiểu chữ in hoa giãn nhẹ, không tô nền đặc. Nút lọc đặc màu trắng
            hay đen hút mắt khỏi sản phẩm — thứ khách thực sự đến để xem. */}
        <div
          className="flex gap-8 mb-12 overflow-x-auto border-b border-line"
          role="tablist"
        >
          {CATEGORIES.map((cat) => {
            const active = currentCategory === cat.value;
            return (
              <button
                key={cat.value}
                role="tab"
                aria-selected={active}
                onClick={() => handleFilterChange(cat.value, 1)}
                className={`relative pb-4 pt-1 text-sm tracking-[0.12em] uppercase whitespace-nowrap min-h-[44px] transition-colors duration-300 ${
                  active
                    ? "text-ink"
                    : "text-muted hover:text-ink"
                }`}
              >
                {cat.label}
                {/* Gạch chân chỉ hiện ở mục đang chọn — dấu hiệu nhẹ nhàng
                    hơn nhiều so với đổi cả nền nút. */}
                <span
                  className={`absolute inset-x-0 bottom-0 h-px transition-opacity duration-300 ${
                    active ? "bg-ink opacity-100" : "opacity-0"
                  }`}
                />
              </button>
            );
          })}
        </div>

        {/* Loading State or Products Grid */}
        {isPending ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5 sm:gap-8">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : initialProducts.length === 0 ? (
          <div className="text-center py-24">
            <svg
              className="w-14 h-14 mx-auto text-brand mb-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1.25}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
            <p className="text-muted text-base max-w-[360px] mx-auto leading-relaxed">
              Hiện tại chưa có sản phẩm nào
              {currentCategory !== "all" && " trong danh mục này"}.
            </p>
          </div>
        ) : (
          <>
            {/* Khoảng cách rộng hơn (32px thay vì 24px): lưới dày đặc trông
                như trang thương mại điện tử, lưới thoáng mới giống showroom. */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5 sm:gap-8">
              {initialProducts.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>

            {/* Pagination */}
            {initialTotalPages > 1 && (
              <nav
                className="flex items-center justify-center gap-2 mt-8"
                aria-label="Phân trang"
              >
                <button
                  onClick={() =>
                    handleFilterChange(currentCategory, Math.max(1, currentPage - 1))
                  }
                  disabled={currentPage === 1}
                  className="px-4 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-ink hover:bg-subtle border border-line"
                  aria-label="Trang trước"
                >
                  ←
                </button>

                {Array.from({ length: initialTotalPages }).map((_, i) => {
                  const pageNum = i + 1;
                  if (
                    pageNum === 1 ||
                    pageNum === initialTotalPages ||
                    Math.abs(pageNum - currentPage) <= 1
                  ) {
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handleFilterChange(currentCategory, pageNum)}
                        aria-current={currentPage === pageNum ? "page" : undefined}
                        className={`px-3 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors ${
                          currentPage === pageNum
                            ? "bg-action text-white"
                            : "bg-white text-ink hover:bg-subtle border border-line"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  }
                  if (pageNum === currentPage - 2 || pageNum === currentPage + 2) {
                    return (
                      <span key={pageNum} className="px-2 text-muted" aria-hidden="true">
                        …
                      </span>
                    );
                  }
                  return null;
                })}

                <button
                  onClick={() =>
                    handleFilterChange(currentCategory, Math.min(initialTotalPages, currentPage + 1))
                  }
                  disabled={currentPage === initialTotalPages}
                  className="px-4 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-ink hover:bg-subtle border border-line"
                  aria-label="Trang sau"
                >
                  →
                </button>
              </nav>
            )}
          </>
        )}
      </div>
    </main>
  );
}

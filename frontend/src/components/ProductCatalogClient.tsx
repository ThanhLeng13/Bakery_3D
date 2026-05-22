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
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          <h1 className="font-heading text-2xl sm:text-3xl lg:text-4xl font-bold text-mocha">
            Danh Mục Bánh Kem
          </h1>
          <p className="mt-2 text-sm sm:text-base text-mocha/70">
            Khám phá bộ sưu tập bánh kem thủ công của chúng tôi
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Category Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2" role="tablist">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              role="tab"
              aria-selected={currentCategory === cat.value}
              onClick={() => handleFilterChange(cat.value, 1)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap min-h-[44px] min-w-[44px] transition-colors ${
                currentCategory === cat.value
                  ? "bg-pink-pastel text-white shadow-sm"
                  : "bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Loading State or Products Grid */}
        {isPending ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        ) : initialProducts.length === 0 ? (
          <div className="text-center py-16">
            <svg
              className="w-16 h-16 mx-auto text-mocha/20 mb-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
              />
            </svg>
            <p className="text-mocha/70 text-lg">
              Hiện tại chưa có sản phẩm nào
              {currentCategory !== "all" && " trong danh mục này"}.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
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
                  className="px-4 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
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
                            ? "bg-pink-pastel text-white"
                            : "bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  }
                  if (pageNum === currentPage - 2 || pageNum === currentPage + 2) {
                    return (
                      <span key={pageNum} className="px-2 text-mocha/40" aria-hidden="true">
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
                  className="px-4 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
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

"use client";

import { useEffect, useState, useCallback } from "react";
import { apiClient } from "@/lib/api";
import { ProductListItem, ProductListResponse } from "@/types";
import ProductCard from "@/components/ProductCard";
import SkeletonCard from "@/components/SkeletonCard";
import Header from "@/components/Header";

type CategoryFilter = "all" | "bánh âu" | "bánh ngọt";

const CATEGORIES: { label: string; value: CategoryFilter }[] = [
  { label: "Tất cả", value: "all" },
  { label: "Bánh Âu", value: "bánh âu" },
  { label: "Bánh Ngọt", value: "bánh ngọt" },
];

const PAGE_SIZE = 20;

export default function ProductCatalogPage() {
  const [products, setProducts] = useState<ProductListItem[]>([]);
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: PAGE_SIZE.toString(),
      });
      if (category !== "all") {
        params.set("category", category);
      }
      const data = await apiClient.get<ProductListResponse>(
        `/api/v1/products?${params.toString()}`
      );
      setProducts(data.products);
      setTotalPages(data.pagination.total_pages);
    } catch {
      setError("Không thể tải danh mục sản phẩm. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  }, [page, category]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const handleCategoryChange = (newCategory: CategoryFilter) => {
    setCategory(newCategory);
    setPage(1);
  };

  return (
    <main className="min-h-screen bg-cream">
      <Header />
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
              aria-selected={category === cat.value}
              onClick={() => handleCategoryChange(cat.value)}
              className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap min-h-[44px] min-w-[44px] transition-colors ${
                category === cat.value
                  ? "bg-pink-pastel text-white shadow-sm"
                  : "bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Error State */}
        {error && (
          <div className="text-center py-12">
            <p className="text-mocha/70 mb-4">{error}</p>
            <button
              onClick={fetchProducts}
              className="px-6 py-2 bg-pink-pastel text-white rounded-full hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && !error && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
            {Array.from({ length: 8 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && products.length === 0 && (
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
              {category !== "all" && " trong danh mục này"}.
            </p>
          </div>
        )}

        {/* Product Grid */}
        {!loading && !error && products.length > 0 && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 sm:gap-6">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <nav
                className="flex items-center justify-center gap-2 mt-8"
                aria-label="Phân trang"
              >
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
                  aria-label="Trang trước"
                >
                  ←
                </button>

                {Array.from({ length: totalPages }).map((_, i) => {
                  const pageNum = i + 1;
                  // Show first, last, current, and adjacent pages
                  if (
                    pageNum === 1 ||
                    pageNum === totalPages ||
                    Math.abs(pageNum - page) <= 1
                  ) {
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setPage(pageNum)}
                        aria-current={page === pageNum ? "page" : undefined}
                        className={`px-3 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors ${
                          page === pageNum
                            ? "bg-pink-pastel text-white"
                            : "bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  }
                  // Show ellipsis
                  if (
                    pageNum === page - 2 ||
                    pageNum === page + 2
                  ) {
                    return (
                      <span
                        key={pageNum}
                        className="px-2 text-mocha/40"
                        aria-hidden="true"
                      >
                        …
                      </span>
                    );
                  }
                  return null;
                })}

                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
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

"use client";

/**
 * Admin product list page with paginated list (20/page),
 * search by name, filter by category/status, and product actions.
 * Validates: Requirements 6.1, 6.6, 6.7
 */

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { apiClient } from "@/lib/api";

interface ProductImage {
  id: string;
  product_id: string;
  url: string;
  sort_order: number;
}

interface Product {
  id: string;
  name: string;
  description: string | null;
  category: string;
  base_price: number;
  sizes: Array<{ name: string; price: number }>;
  flavors: string[];
  is_active: boolean;
  images: ProductImage[];
  created_at: string;
  updated_at: string;
}

interface ProductListResponse {
  products: Product[];
  total: number;
  page: number;
  page_size: number;
}

const PAGE_SIZE = 20;

const CATEGORIES = [
  { value: "", label: "Tất cả danh mục" },
  { value: "bánh âu", label: "Bánh Âu" },
  { value: "bánh ngọt", label: "Bánh Ngọt" },
  { value: "bánh kem", label: "Bánh Kem" },
  { value: "bánh sinh nhật", label: "Bánh Sinh Nhật" },
  { value: "bánh cưới", label: "Bánh Cưới" },
];

const STATUS_OPTIONS = [
  { value: "", label: "Tất cả trạng thái" },
  { value: "active", label: "Đang bán" },
  { value: "inactive", label: "Ngừng bán" },
];

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(PAGE_SIZE));
      if (search.trim()) params.set("search", search.trim());
      if (category) params.set("category", category);
      if (status) params.set("is_active", status === "active" ? "true" : "false");

      const data = await apiClient.get<ProductListResponse>(
        `/api/v1/admin/products?${params.toString()}`
      );
      setProducts(data.products);
      setTotal(data.total);
    } catch {
      setProducts([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, search, category, status]);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [search, category, status]);

  const handleToggleStatus = async (product: Product) => {
    setTogglingId(product.id);
    try {
      await apiClient.patch(`/api/v1/admin/products/${product.id}/status`, {
        is_active: !product.is_active,
      });
      // Update local state
      setProducts((prev) =>
        prev.map((p) =>
          p.id === product.id ? { ...p, is_active: !p.is_active } : p
        )
      );
    } catch {
      // Error handled silently, could add toast notification
    } finally {
      setTogglingId(null);
    }
  };

  const formatPrice = (price: number) => {
    return new Intl.NumberFormat("vi-VN").format(price) + "₫";
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl text-mocha font-bold">
            Quản lý sản phẩm
          </h1>
          <p className="text-sm text-mocha/60 font-body mt-1">
            {total} sản phẩm
          </p>
        </div>
        <Link
          href="/admin/products/new"
          className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-pink-pastel text-white font-body text-sm font-medium rounded-lg hover:bg-pink-pastel/90 transition-colors shadow-sm"
        >
          <span>+</span>
          Tạo sản phẩm mới
        </Link>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-xl p-4 shadow-sm border border-mocha/5">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* Search */}
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-mocha/40">
              🔍
            </span>
            <input
              type="text"
              placeholder="Tìm theo tên sản phẩm..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-mocha/10 bg-cream/50 font-body text-sm text-mocha placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel/50"
            />
          </div>

          {/* Category filter */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-mocha/10 bg-cream/50 font-body text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel/50"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full px-4 py-2.5 rounded-lg border border-mocha/10 bg-cream/50 font-body text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel/50"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Product table */}
      <div className="bg-white rounded-xl shadow-sm border border-mocha/5 overflow-hidden">
        {loading ? (
          <ProductListSkeleton />
        ) : products.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-mocha/50 font-body">
              Không tìm thấy sản phẩm nào.
            </p>
          </div>
        ) : (
          <>
            {/* Desktop table */}
            <div className="hidden md:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-mocha/5 bg-cream/30">
                    <th className="text-left px-4 py-3 font-body text-xs font-medium text-mocha/60 uppercase tracking-wider">
                      Sản phẩm
                    </th>
                    <th className="text-left px-4 py-3 font-body text-xs font-medium text-mocha/60 uppercase tracking-wider">
                      Danh mục
                    </th>
                    <th className="text-left px-4 py-3 font-body text-xs font-medium text-mocha/60 uppercase tracking-wider">
                      Giá
                    </th>
                    <th className="text-left px-4 py-3 font-body text-xs font-medium text-mocha/60 uppercase tracking-wider">
                      Trạng thái
                    </th>
                    <th className="text-right px-4 py-3 font-body text-xs font-medium text-mocha/60 uppercase tracking-wider">
                      Thao tác
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-mocha/5">
                  {products.map((product) => (
                    <tr
                      key={product.id}
                      className="hover:bg-cream/20 transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-12 h-12 rounded-lg bg-cream flex items-center justify-center overflow-hidden flex-shrink-0">
                            {product.images.length > 0 ? (
                              <img
                                src={product.images[0].url}
                                alt={product.name}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <span className="text-2xl">🎂</span>
                            )}
                          </div>
                          <span className="font-body text-sm text-mocha font-medium line-clamp-1">
                            {product.name}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2.5 py-1 rounded-full bg-cream text-xs font-body text-mocha/70">
                          {product.category}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-body text-sm text-mocha">
                        {formatPrice(product.base_price)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleToggleStatus(product)}
                          disabled={togglingId === product.id}
                          className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 disabled:opacity-50"
                          style={{
                            backgroundColor: product.is_active
                              ? "#E8837A"
                              : "#d1d5db",
                          }}
                          aria-label={
                            product.is_active
                              ? "Ngừng bán sản phẩm"
                              : "Kích hoạt sản phẩm"
                          }
                        >
                          <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm ${
                              product.is_active
                                ? "translate-x-6"
                                : "translate-x-1"
                            }`}
                          />
                        </button>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/admin/products/${product.id}/edit`}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-body text-pink-pastel hover:bg-pink-pastel/10 transition-colors"
                        >
                          ✏️ Sửa
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile card list */}
            <div className="md:hidden divide-y divide-mocha/5">
              {products.map((product) => (
                <div key={product.id} className="p-4 space-y-3">
                  <div className="flex items-center gap-3">
                    <div className="w-14 h-14 rounded-lg bg-cream flex items-center justify-center overflow-hidden flex-shrink-0">
                      {product.images.length > 0 ? (
                        <img
                          src={product.images[0].url}
                          alt={product.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <span className="text-2xl">🎂</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-body text-sm text-mocha font-medium truncate">
                        {product.name}
                      </p>
                      <p className="font-body text-xs text-mocha/60">
                        {product.category} · {formatPrice(product.base_price)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => handleToggleStatus(product)}
                      disabled={togglingId === product.id}
                      className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 disabled:opacity-50"
                      style={{
                        backgroundColor: product.is_active
                          ? "#E8837A"
                          : "#d1d5db",
                      }}
                      aria-label={
                        product.is_active
                          ? "Ngừng bán sản phẩm"
                          : "Kích hoạt sản phẩm"
                      }
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm ${
                          product.is_active
                            ? "translate-x-6"
                            : "translate-x-1"
                        }`}
                      />
                    </button>
                    <Link
                      href={`/admin/products/${product.id}/edit`}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-body text-pink-pastel hover:bg-pink-pastel/10 transition-colors"
                    >
                      ✏️ Sửa
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-2 rounded-lg font-body text-sm text-mocha/70 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            ← Trước
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              let pageNum: number;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (page <= 3) {
                pageNum = i + 1;
              } else if (page >= totalPages - 2) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = page - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={`w-9 h-9 rounded-lg font-body text-sm transition-colors ${
                    page === pageNum
                      ? "bg-pink-pastel text-white font-medium"
                      : "text-mocha/70 hover:bg-white"
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-2 rounded-lg font-body text-sm text-mocha/70 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Sau →
          </button>
        </div>
      )}
    </div>
  );
}

function ProductListSkeleton() {
  return (
    <div className="p-4 space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 animate-pulse">
          <div className="w-12 h-12 rounded-lg bg-mocha/5" />
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-mocha/5 rounded w-1/3" />
            <div className="h-3 bg-mocha/5 rounded w-1/4" />
          </div>
          <div className="h-6 w-11 bg-mocha/5 rounded-full" />
        </div>
      ))}
    </div>
  );
}

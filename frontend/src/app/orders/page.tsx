"use client";

/**
 * Order History page.
 * Protected route - requires authentication.
 * Displays paginated list of customer orders with status badges and pickup dates.
 *
 * Validates: Requirements 4.6
 */

import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { apiClient } from "@/lib/api";
import type { OrderStatus, PaginationMeta } from "@/types";

interface OrderListItem {
  id: string;
  status: OrderStatus;
  total_price: number;
  pickup_date: string;
  customer_name: string;
  created_at: string;
  items_count: number;
}

interface OrderListResponse {
  orders: OrderListItem[];
  pagination: PaginationMeta;
}

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  in_production: "Đang làm",
  ready: "Sẵn sàng",
  delivered: "Đã giao",
};

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  confirmed: "bg-blue-100 text-blue-800",
  in_production: "bg-orange-100 text-orange-800",
  ready: "bg-green-100 text-green-800",
  delivered: "bg-gray-100 text-gray-800",
};

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN").format(price) + "đ";
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const PAGE_SIZE = 10;

function OrderHistoryContent() {
  const router = useRouter();
  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: PAGE_SIZE.toString(),
      });
      const data = await apiClient.get<OrderListResponse>(
        `/api/v1/orders?${params.toString()}`
      );
      setOrders(data.orders);
      setTotalPages(data.pagination.total_pages);
    } catch {
      setError("Không thể tải danh sách đơn hàng. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  return (
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.push("/")}
            className="font-heading text-lg text-mocha font-bold flex items-center gap-1.5 hover:text-pink-pastel transition-colors min-h-[44px]"
            aria-label="Về trang chủ"
            title="Về trang chủ"
          >
            🎂 <span className="hidden sm:inline">Bơ Nơ</span>
          </button>
          <span className="text-mocha/20">|</span>
          <h1 className="font-heading text-xl md:text-2xl text-mocha font-bold">
            Đơn hàng của tôi
          </h1>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        {/* Error State */}
        {error && (
          <div className="text-center py-12">
            <p className="text-mocha/70 mb-4">{error}</p>
            <button
              onClick={fetchOrders}
              className="px-6 py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
            >
              Thử lại
            </button>
          </div>
        )}

        {/* Loading State */}
        {loading && !error && (
          <div className="space-y-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl p-5 animate-pulse">
                <div className="flex justify-between items-start mb-3">
                  <div className="h-4 bg-mocha/10 rounded w-24" />
                  <div className="h-6 bg-mocha/10 rounded-full w-20" />
                </div>
                <div className="h-3 bg-mocha/10 rounded w-32 mb-2" />
                <div className="h-3 bg-mocha/10 rounded w-40" />
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && orders.length === 0 && (
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
                d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            <p className="text-mocha/70 text-lg mb-2">
              Bạn chưa có đơn hàng nào
            </p>
            <p className="text-mocha/50 text-sm mb-6">
              Hãy thiết kế bánh kem và đặt hàng ngay!
            </p>
            <button
              onClick={() => router.push("/cake-builder")}
              className="px-6 py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
            >
              Thiết kế bánh kem
            </button>
          </div>
        )}

        {/* Order List */}
        {!loading && !error && orders.length > 0 && (
          <>
            <div className="space-y-4">
              {orders.map((order) => (
                <button
                  key={order.id}
                  onClick={() => router.push(`/orders/${order.id}`)}
                  className="w-full bg-white rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow text-left min-h-[44px]"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <span className="text-xs text-mocha/50 font-mono">
                        #{order.id.slice(0, 8).toUpperCase()}
                      </span>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-medium ${STATUS_STYLES[order.status]}`}
                    >
                      {STATUS_LABELS[order.status]}
                    </span>
                  </div>

                  <div className="flex justify-between items-end">
                    <div className="space-y-1">
                      <p className="text-sm text-mocha/70">
                        <span className="inline-block w-4 mr-1">📅</span>
                        Nhận: {formatDate(order.pickup_date)}
                      </p>
                      <p className="text-xs text-mocha/50">
                        Đặt: {formatDate(order.created_at)}
                      </p>
                    </div>
                    <span className="font-bold text-pink-pastel">
                      {formatPrice(order.total_price)}
                    </span>
                  </div>
                </button>
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
                  if (pageNum === page - 2 || pageNum === page + 2) {
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

export default function OrderHistoryPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-cream">
          <div className="animate-pulse flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-pink-pastel/30" />
            <p className="text-mocha/60 font-body">Đang tải...</p>
          </div>
        </div>
      }
    >
      <ProtectedRoute>
        <OrderHistoryContent />
      </ProtectedRoute>
    </Suspense>
  );
}

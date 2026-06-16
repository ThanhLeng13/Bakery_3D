"use client";

/**
 * Admin Orders Management page.
 * Protected route - requires admin role.
 * Lists all orders with status/date/name filters, pagination,
 * and ability to update order status.
 *
 * Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
 */

import { useEffect, useState, useCallback, Suspense } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import type { OrderStatus, PaginationMeta } from "@/types";
import CustomizationDetails from "@/components/CustomizationDetails";

interface AdminOrder {
  id: string;
  status: OrderStatus;
  total_price: number;
  pickup_date: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string;
  ai_summary?: string;
  baker_notes?: string;
  created_at: string;
  updated_at: string;
}

interface AdminOrdersResponse {
  orders: AdminOrder[];
  pagination: PaginationMeta;
}

interface OrderDetailFull extends AdminOrder {
  items: Array<{
    id: string;
    product_id: string;
    size: string;
    flavor: string;
    quantity: number;
    unit_price: number;
  }>;
  customizations: Array<{
    id: string;
    customization_json: Record<string, unknown>;
  }>;
  status_history: Array<{
    id: string;
    old_status: string | null;
    new_status: string;
    changed_by: string;
    changed_at: string;
  }>;
}

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  in_production: "Đang làm",
  ready: "Sẵn sàng",
  delivered: "Đã giao",
};

const STATUS_STYLES: Record<OrderStatus, string> = {
  pending: "bg-yellow-100 text-yellow-800 border-yellow-200",
  confirmed: "bg-blue-100 text-blue-800 border-blue-200",
  in_production: "bg-orange-100 text-orange-800 border-orange-200",
  ready: "bg-green-100 text-green-800 border-green-200",
  delivered: "bg-gray-100 text-gray-700 border-gray-200",
};

// Valid admin transitions
const ADMIN_TRANSITIONS: Partial<Record<OrderStatus, OrderStatus>> = {
  pending: "confirmed",
  ready: "delivered",
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

const PAGE_SIZE = 20;
const ALL_STATUSES: OrderStatus[] = [
  "pending",
  "confirmed",
  "in_production",
  "ready",
  "delivered",
];

function AdminOrdersContent() {
  const router = useRouter();
  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerNameInput, setCustomerNameInput] = useState("");

  // Detail modal
  const [selectedOrder, setSelectedOrder] = useState<OrderDetailFull | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [statusUpdateMsg, setStatusUpdateMsg] = useState("");

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: PAGE_SIZE.toString(),
      });
      if (statusFilter) params.append("status", statusFilter);
      if (dateFrom) params.append("date_from", new Date(dateFrom).toISOString());
      if (dateTo) params.append("date_to", new Date(dateTo + "T23:59:59").toISOString());
      if (customerName && customerName.length >= 2) params.append("customer_name", customerName);

      const data = await apiClient.get<AdminOrdersResponse>(
        `/api/v1/admin/orders?${params.toString()}`
      );
      setOrders(data.orders);
      setTotalPages(data.pagination.total_pages);
      setTotalItems(data.pagination.total_items);
    } catch {
      setError("Không thể tải danh sách đơn hàng. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, dateFrom, dateTo, customerName]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  async function openOrderDetail(orderId: string) {
    setDetailLoading(true);
    setStatusUpdateMsg("");
    try {
      const data = await apiClient.get<OrderDetailFull>(`/api/v1/admin/orders/${orderId}`);
      setSelectedOrder(data);
    } catch {
      alert("Không thể tải chi tiết đơn hàng.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleStatusUpdate(orderId: string, newStatus: string) {
    setUpdatingStatus(true);
    setStatusUpdateMsg("");
    try {
      await apiClient.patch(`/api/v1/orders/${orderId}/status`, { status: newStatus });
      setStatusUpdateMsg("✓ Cập nhật trạng thái thành công!");
      // Refresh detail
      const data = await apiClient.get<OrderDetailFull>(`/api/v1/admin/orders/${orderId}`);
      setSelectedOrder(data);
      // Refresh list
      fetchOrders();
    } catch {
      setStatusUpdateMsg("✗ Cập nhật thất bại. Vui lòng thử lại.");
    } finally {
      setUpdatingStatus(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setCustomerName(customerNameInput);
    setPage(1);
  }

  function handleClearFilters() {
    setStatusFilter("");
    setDateFrom("");
    setDateTo("");
    setCustomerName("");
    setCustomerNameInput("");
    setPage(1);
  }

  return (
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/admin/products")}
              className="text-mocha hover:text-pink-pastel transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Về trang sản phẩm"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <div>
              <h1 className="font-heading text-xl md:text-2xl text-mocha font-bold">
                Quản lý đơn hàng
              </h1>
              <p className="text-xs text-mocha/50">{totalItems} đơn hàng</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Filters */}
        <section className="bg-white rounded-2xl shadow-sm p-4 md:p-6">
          <h2 className="font-semibold text-mocha mb-4 text-sm uppercase tracking-wide">Bộ lọc</h2>
          <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Customer name */}
            <div>
              <label className="block text-xs font-medium text-mocha/70 mb-1">Tên khách hàng</label>
              <input
                type="text"
                value={customerNameInput}
                onChange={(e) => setCustomerNameInput(e.target.value)}
                placeholder="Tìm theo tên..."
                minLength={2}
                className="w-full px-3 py-2 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px]"
              />
            </div>

            {/* Status filter */}
            <div>
              <label className="block text-xs font-medium text-mocha/70 mb-1">Trạng thái</label>
              <select
                value={statusFilter}
                onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px]"
              >
                <option value="">Tất cả</option>
                {ALL_STATUSES.map((s) => (
                  <option key={s} value={s}>{STATUS_LABELS[s]}</option>
                ))}
              </select>
            </div>

            {/* Date from */}
            <div>
              <label className="block text-xs font-medium text-mocha/70 mb-1">Từ ngày</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px]"
              />
            </div>

            {/* Date to */}
            <div>
              <label className="block text-xs font-medium text-mocha/70 mb-1">Đến ngày</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
                className="w-full px-3 py-2 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px]"
              />
            </div>

            {/* Actions */}
            <div className="sm:col-span-2 lg:col-span-4 flex gap-2">
              <button
                type="submit"
                className="px-4 py-2 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
              >
                Tìm kiếm
              </button>
              <button
                type="button"
                onClick={handleClearFilters}
                className="px-4 py-2 bg-white text-mocha border border-mocha/20 rounded-full text-sm font-medium hover:bg-cream transition-colors min-h-[44px]"
              >
                Xóa bộ lọc
              </button>
            </div>
          </form>
        </section>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm flex justify-between items-center">
            <span>{error}</span>
            <button onClick={fetchOrders} className="text-red-600 underline text-sm ml-2">Thử lại</button>
          </div>
        )}

        {/* Loading skeleton */}
        {loading && !error && (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl p-4 animate-pulse">
                <div className="flex justify-between">
                  <div className="h-4 bg-mocha/10 rounded w-32" />
                  <div className="h-6 bg-mocha/10 rounded-full w-24" />
                </div>
                <div className="mt-2 h-3 bg-mocha/10 rounded w-48" />
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && orders.length === 0 && (
          <div className="text-center py-16 bg-white rounded-2xl">
            <svg className="w-16 h-16 mx-auto text-mocha/20 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-mocha/70 text-lg">Không tìm thấy đơn hàng nào</p>
            <p className="text-mocha/40 text-sm mt-1">Thử thay đổi bộ lọc</p>
          </div>
        )}

        {/* Orders table */}
        {!loading && !error && orders.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-mocha/10 bg-cream/50">
                    <th className="text-left px-4 py-3 font-semibold text-mocha/70 text-xs uppercase tracking-wide">Mã đơn</th>
                    <th className="text-left px-4 py-3 font-semibold text-mocha/70 text-xs uppercase tracking-wide">Khách hàng</th>
                    <th className="text-left px-4 py-3 font-semibold text-mocha/70 text-xs uppercase tracking-wide">Ngày nhận</th>
                    <th className="text-left px-4 py-3 font-semibold text-mocha/70 text-xs uppercase tracking-wide">Tổng tiền</th>
                    <th className="text-left px-4 py-3 font-semibold text-mocha/70 text-xs uppercase tracking-wide">Trạng thái</th>
                    <th className="text-left px-4 py-3 font-semibold text-mocha/70 text-xs uppercase tracking-wide">Ngày đặt</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-mocha/5">
                  {orders.map((order) => (
                    <tr key={order.id} className="hover:bg-cream/30 transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs text-mocha/60">
                          #{order.id.slice(0, 8).toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <p className="font-medium text-mocha">{order.customer_name}</p>
                        <p className="text-xs text-mocha/50">{order.customer_phone}</p>
                      </td>
                      <td className="px-4 py-3 text-mocha/70 whitespace-nowrap">
                        {formatDate(order.pickup_date)}
                      </td>
                      <td className="px-4 py-3 font-bold text-pink-pastel whitespace-nowrap">
                        {formatPrice(order.total_price)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium border ${STATUS_STYLES[order.status]}`}>
                          {STATUS_LABELS[order.status]}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-mocha/50 whitespace-nowrap text-xs">
                        {formatDate(order.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => openOrderDetail(order.id)}
                          className="px-3 py-1.5 bg-pink-pastel/10 text-pink-pastel rounded-full text-xs font-medium hover:bg-pink-pastel hover:text-white transition-colors min-h-[44px] flex items-center"
                        >
                          Chi tiết
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 p-4 border-t border-mocha/5">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-3 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
                >
                  ←
                </button>
                <span className="text-sm text-mocha/70">
                  Trang {page}/{totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="px-3 py-2 rounded-full text-sm font-medium min-h-[44px] min-w-[44px] transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-white text-mocha hover:bg-pink-pastel/10 border border-mocha/10"
                >
                  →
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Order Detail Modal */}
      {(selectedOrder || detailLoading) && (
        <div className="fixed inset-0 bg-mocha/50 backdrop-blur-sm z-50 flex items-start justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl my-4">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-mocha/10">
              <h2 className="font-heading text-lg font-bold text-mocha">
                Chi tiết đơn hàng
                {selectedOrder && (
                  <span className="ml-2 font-mono text-sm text-mocha/50">
                    #{selectedOrder.id.slice(0, 8).toUpperCase()}
                  </span>
                )}
              </h2>
              <button
                onClick={() => { setSelectedOrder(null); setStatusUpdateMsg(""); }}
                className="text-mocha/50 hover:text-mocha transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label="Đóng"
              >
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            {detailLoading ? (
              <div className="p-8 flex items-center justify-center">
                <div className="animate-spin w-8 h-8 border-2 border-pink-pastel border-t-transparent rounded-full" />
              </div>
            ) : selectedOrder ? (
              <div className="p-5 space-y-5">
                {/* Status update feedback */}
                {statusUpdateMsg && (
                  <div className={`text-sm px-4 py-3 rounded-xl ${statusUpdateMsg.startsWith("✓") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                    {statusUpdateMsg}
                  </div>
                )}

                {/* Customer info */}
                <section className="bg-cream rounded-xl p-4 space-y-2">
                  <h3 className="font-semibold text-mocha text-sm mb-3">Thông tin khách hàng</h3>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-mocha/50 text-xs">Tên</span>
                      <p className="font-medium text-mocha">{selectedOrder.customer_name}</p>
                    </div>
                    <div>
                      <span className="text-mocha/50 text-xs">SĐT</span>
                      <p className="font-medium text-mocha">{selectedOrder.customer_phone}</p>
                    </div>
                    {selectedOrder.customer_email && (
                      <div className="col-span-2">
                        <span className="text-mocha/50 text-xs">Email</span>
                        <p className="font-medium text-mocha">{selectedOrder.customer_email}</p>
                      </div>
                    )}
                    <div>
                      <span className="text-mocha/50 text-xs">Ngày nhận</span>
                      <p className="font-medium text-mocha">{formatDate(selectedOrder.pickup_date)}</p>
                    </div>
                    <div>
                      <span className="text-mocha/50 text-xs">Tổng tiền</span>
                      <p className="font-bold text-pink-pastel">{formatPrice(selectedOrder.total_price)}</p>
                    </div>
                  </div>
                </section>

                {/* Current status + update */}
                <section className="bg-cream rounded-xl p-4">
                  <h3 className="font-semibold text-mocha text-sm mb-3">Trạng thái đơn hàng</h3>
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className={`px-3 py-1.5 rounded-full text-sm font-medium border ${STATUS_STYLES[selectedOrder.status]}`}>
                      {STATUS_LABELS[selectedOrder.status]}
                    </span>
                    {ADMIN_TRANSITIONS[selectedOrder.status] && (
                      <button
                        onClick={() => handleStatusUpdate(selectedOrder.id, ADMIN_TRANSITIONS[selectedOrder.status]!)}
                        disabled={updatingStatus}
                        className="px-4 py-2 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-50 min-h-[44px]"
                      >
                        {updatingStatus ? "Đang cập nhật..." : `→ ${STATUS_LABELS[ADMIN_TRANSITIONS[selectedOrder.status]!]}`}
                      </button>
                    )}
                  </div>
                </section>

                {/* Order items */}
                {selectedOrder.items && selectedOrder.items.length > 0 && (
                  <section>
                    <h3 className="font-semibold text-mocha text-sm mb-3">Sản phẩm</h3>
                    <div className="space-y-2">
                      {selectedOrder.items.map((item) => (
                        <div key={item.id} className="flex justify-between items-center bg-cream rounded-xl p-3 text-sm">
                          <div>
                            <p className="font-medium text-mocha">Bánh kem {item.size}</p>
                            <p className="text-mocha/60 text-xs">{item.flavor} × {item.quantity}</p>
                          </div>
                          <span className="font-bold text-mocha">{formatPrice(item.unit_price * item.quantity)}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Customization details - Full baker/admin view */}
                {selectedOrder.customizations && selectedOrder.customizations.length > 0 && (
                  <section className="border-2 border-pink-300 rounded-xl overflow-hidden">
                    <div className="bg-pink-500 px-4 py-2 flex items-center gap-2">
                      <span className="text-lg">🎂</span>
                      <h3 className="font-bold text-white text-sm">Yêu cầu tùy chỉnh bánh của khách</h3>
                    </div>
                    {selectedOrder.customizations.map((c) => (
                      <CustomizationDetails key={c.id} customizationJson={c.customization_json} />
                    ))}
                  </section>
                )}

                {selectedOrder.ai_summary && (
                  <section className="bg-purple-50 rounded-xl p-4">
                    <h3 className="font-semibold text-purple-800 text-sm mb-2">AI Tư vấn</h3>
                    <p className="text-purple-700 text-sm whitespace-pre-wrap">{selectedOrder.ai_summary}</p>
                  </section>
                )}

                {/* Baker notes */}
                {selectedOrder.baker_notes && (
                  <section className="bg-orange-50 rounded-xl p-4">
                    <h3 className="font-semibold text-orange-800 text-sm mb-2">Ghi chú thợ bánh</h3>
                    <p className="text-orange-700 text-sm">{selectedOrder.baker_notes}</p>
                  </section>
                )}

                {/* Status history */}
                {selectedOrder.status_history && selectedOrder.status_history.length > 0 && (
                  <section>
                    <h3 className="font-semibold text-mocha text-sm mb-3">Lịch sử trạng thái</h3>
                    <div className="space-y-2">
                      {selectedOrder.status_history.map((h) => (
                        <div key={h.id} className="flex items-center gap-2 text-xs text-mocha/70">
                          <div className="w-2 h-2 rounded-full bg-pink-pastel flex-shrink-0" />
                          <span>{h.old_status ? `${STATUS_LABELS[h.old_status as OrderStatus]} →` : "Tạo mới →"}</span>
                          <span className="font-medium text-mocha">{STATUS_LABELS[h.new_status as OrderStatus]}</span>
                          <span className="ml-auto text-mocha/40">{formatDate(h.changed_at)}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}
    </main>
  );
}

export default function AdminOrdersPage() {
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
      <AdminOrdersContent />
    </Suspense>
  );
}

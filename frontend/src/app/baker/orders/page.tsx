"use client";

/**
 * Baker Dashboard page.
 * Protected route - requires baker role.
 * Shows orders with status confirmed or in_production,
 * sorted by pickup_date ascending.
 * Baker can update status and add/edit notes.
 *
 * Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5
 */

import { useEffect, useState, useCallback, Suspense } from "react";
import { apiClient } from "@/lib/api";
import type { OrderStatus } from "@/types";
import ProtectedRoute from "@/components/ProtectedRoute";
import Link from "next/link";

interface BakerOrder {
  id: string;
  status: OrderStatus;
  total_price: number;
  pickup_date: string;
  customer_name: string;
  customer_phone: string;
  ai_summary?: string;
  baker_notes?: string;
  created_at: string;
  updated_at: string;
}

interface BakerOrdersResponse {
  orders: BakerOrder[];
  total: number;
}

interface BakerOrderDetail extends BakerOrder {
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
    changed_at: string;
  }>;
}

const STATUS_LABELS: Record<string, string> = {
  confirmed: "Đã xác nhận",
  in_production: "Đang làm",
  ready: "Sẵn sàng",
};

const STATUS_STYLES: Record<string, string> = {
  confirmed: "bg-blue-100 text-blue-800 border-blue-200",
  in_production: "bg-orange-100 text-orange-800 border-orange-200",
  ready: "bg-green-100 text-green-800 border-green-200",
};

// Baker valid transitions
const BAKER_NEXT_STATUS: Record<string, string> = {
  confirmed: "in_production",
  in_production: "ready",
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

function getTimeUrgency(pickupDate: string): "urgent" | "soon" | "normal" {
  const now = new Date();
  const pickup = new Date(pickupDate);
  const hoursLeft = (pickup.getTime() - now.getTime()) / (1000 * 60 * 60);

  if (hoursLeft < 12) return "urgent";
  if (hoursLeft < 24) return "soon";
  return "normal";
}

function BakerDashboardContent() {
  const [orders, setOrders] = useState<BakerOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail modal
  const [selectedOrder, setSelectedOrder] = useState<BakerOrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [savingNotes, setSavingNotes] = useState(false);
  const [bakerNotesInput, setBakerNotesInput] = useState("");
  const [actionMsg, setActionMsg] = useState("");

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.get<BakerOrdersResponse>("/api/v1/baker/orders");
      setOrders(data.orders);
    } catch {
      setError("Không thể tải danh sách đơn hàng. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrders();
    // Auto refresh every 60 seconds
    const interval = setInterval(fetchOrders, 60000);
    return () => clearInterval(interval);
  }, [fetchOrders]);

  async function openOrderDetail(orderId: string) {
    setDetailLoading(true);
    setActionMsg("");
    try {
      const data = await apiClient.get<BakerOrderDetail>(`/api/v1/baker/orders/${orderId}`);
      setSelectedOrder(data);
      setBakerNotesInput(data.baker_notes || "");
    } catch {
      alert("Không thể tải chi tiết đơn hàng.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function handleStatusUpdate(orderId: string, newStatus: string) {
    setUpdatingStatus(true);
    setActionMsg("");
    try {
      await apiClient.patch(`/api/v1/baker/orders/${orderId}/status`, { status: newStatus });
      setActionMsg("✓ Cập nhật trạng thái thành công!");
      // Refresh
      const data = await apiClient.get<BakerOrderDetail>(`/api/v1/baker/orders/${orderId}`);
      setSelectedOrder(data);
      fetchOrders();
    } catch {
      setActionMsg("✗ Cập nhật thất bại. Vui lòng thử lại.");
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleSaveNotes(orderId: string) {
    setSavingNotes(true);
    setActionMsg("");
    try {
      await apiClient.patch(`/api/v1/baker/orders/${orderId}/notes`, { notes: bakerNotesInput });
      setActionMsg("✓ Đã lưu ghi chú!");
      setSelectedOrder((prev) => prev ? { ...prev, baker_notes: bakerNotesInput } : null);
      fetchOrders();
    } catch {
      setActionMsg("✗ Lưu ghi chú thất bại.");
    } finally {
      setSavingNotes(false);
    }
  }

  const urgentOrders = orders.filter((o) => getTimeUrgency(o.pickup_date) === "urgent");
  const soonOrders = orders.filter((o) => getTimeUrgency(o.pickup_date) === "soon");
  const normalOrders = orders.filter((o) => getTimeUrgency(o.pickup_date) === "normal");

  return (
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="font-heading text-xl md:text-2xl text-mocha font-bold">
              Bảng điều khiển thợ bánh
            </h1>
            <p className="text-xs text-mocha/50">
              {orders.length} đơn hàng đang hoạt động
              {urgentOrders.length > 0 && (
                <span className="ml-2 text-red-600 font-medium">
                  ⚠ {urgentOrders.length} đơn khẩn
                </span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="text-sm font-medium text-mocha/60 hover:text-pink-pastel transition-colors flex items-center gap-1.5 mr-2 px-3 py-1.5 rounded-full hover:bg-cream"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
              <span>Trang chủ</span>
            </Link>
            <button
              onClick={fetchOrders}
              className="p-2 text-mocha/60 hover:text-pink-pastel transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center rounded-full hover:bg-cream"
              title="Làm mới"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M23 4v6h-6M1 20v-6h6" />
                <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm flex justify-between">
            <span>{error}</span>
            <button onClick={fetchOrders} className="underline">Thử lại</button>
          </div>
        )}

        {/* Loading */}
        {loading && !error && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl p-4 animate-pulse">
                <div className="h-4 bg-mocha/10 rounded w-1/3 mb-2" />
                <div className="h-3 bg-mocha/10 rounded w-1/2" />
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !error && orders.length === 0 && (
          <div className="text-center py-20 bg-white rounded-2xl">
            <div className="text-6xl mb-4">🎂</div>
            <h2 className="font-heading text-xl text-mocha font-bold mb-2">
              Không có đơn hàng nào
            </h2>
            <p className="text-mocha/60">Hiện tại không có đơn hàng nào cần xử lý.</p>
          </div>
        )}

        {/* Urgent orders */}
        {!loading && !error && urgentOrders.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-red-500 text-lg">🚨</span>
              <h2 className="font-semibold text-red-600 text-sm uppercase tracking-wide">
                Khẩn cấp (dưới 12 giờ)
              </h2>
            </div>
            <div className="space-y-3">
              {urgentOrders.map((order) => (
                <OrderCard key={order.id} order={order} urgency="urgent" onClick={() => openOrderDetail(order.id)} />
              ))}
            </div>
          </section>
        )}

        {/* Soon orders */}
        {!loading && !error && soonOrders.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-orange-500 text-lg">⏰</span>
              <h2 className="font-semibold text-orange-600 text-sm uppercase tracking-wide">
                Sắp đến (12-24 giờ)
              </h2>
            </div>
            <div className="space-y-3">
              {soonOrders.map((order) => (
                <OrderCard key={order.id} order={order} urgency="soon" onClick={() => openOrderDetail(order.id)} />
              ))}
            </div>
          </section>
        )}

        {/* Normal orders */}
        {!loading && !error && normalOrders.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-green-500 text-lg">✅</span>
              <h2 className="font-semibold text-green-600 text-sm uppercase tracking-wide">
                Còn thời gian (hơn 24 giờ)
              </h2>
            </div>
            <div className="space-y-3">
              {normalOrders.map((order) => (
                <OrderCard key={order.id} order={order} urgency="normal" onClick={() => openOrderDetail(order.id)} />
              ))}
            </div>
          </section>
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
                onClick={() => { setSelectedOrder(null); setActionMsg(""); }}
                className="text-mocha/50 hover:text-mocha transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
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
                {/* Action feedback */}
                {actionMsg && (
                  <div className={`text-sm px-4 py-3 rounded-xl ${actionMsg.startsWith("✓") ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
                    {actionMsg}
                  </div>
                )}

                {/* Status + update */}
                <section className="bg-cream rounded-xl p-4">
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div>
                      <p className="text-xs text-mocha/50 mb-1">Trạng thái hiện tại</p>
                      <span className={`px-3 py-1.5 rounded-full text-sm font-medium border ${STATUS_STYLES[selectedOrder.status] || "bg-gray-100 text-gray-700"}`}>
                        {STATUS_LABELS[selectedOrder.status] || selectedOrder.status}
                      </span>
                    </div>
                    {BAKER_NEXT_STATUS[selectedOrder.status] && (
                      <button
                        onClick={() => handleStatusUpdate(selectedOrder.id, BAKER_NEXT_STATUS[selectedOrder.status])}
                        disabled={updatingStatus}
                        className="px-4 py-2 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-50 min-h-[44px]"
                      >
                        {updatingStatus ? "Đang cập nhật..." : `→ ${STATUS_LABELS[BAKER_NEXT_STATUS[selectedOrder.status]]}`}
                      </button>
                    )}
                  </div>
                </section>

                {/* Customer + Pickup */}
                <section className="bg-cream rounded-xl p-4 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-mocha/50 mb-1">Khách hàng</p>
                    <p className="font-medium text-mocha">{selectedOrder.customer_name}</p>
                    <p className="text-xs text-mocha/60">{selectedOrder.customer_phone}</p>
                  </div>
                  <div>
                    <p className="text-xs text-mocha/50 mb-1">Ngày nhận bánh</p>
                    <p className="font-medium text-mocha">{formatDate(selectedOrder.pickup_date)}</p>
                    <p className="font-bold text-pink-pastel">{formatPrice(selectedOrder.total_price)}</p>
                  </div>
                </section>

                {/* Order items */}
                {selectedOrder.items && selectedOrder.items.length > 0 && (
                  <section>
                    <h3 className="font-semibold text-mocha text-sm mb-3">Sản phẩm</h3>
                    {selectedOrder.items.map((item) => (
                      <div key={item.id} className="bg-cream rounded-xl p-3 text-sm flex justify-between items-center mb-2">
                        <div>
                          <p className="font-medium text-mocha">🎂 Bánh kem {item.size}</p>
                          <p className="text-xs text-mocha/60">{item.flavor} × {item.quantity}</p>
                        </div>
                        <span className="text-mocha font-bold">{formatPrice(item.unit_price * item.quantity)}</span>
                      </div>
                    ))}
                  </section>
                )}

                {/* Customization details - Full baker view */}
                {selectedOrder.customizations && selectedOrder.customizations.length > 0 && (
                  <section className="border-2 border-pink-300 rounded-xl overflow-hidden">
                    <div className="bg-pink-500 px-4 py-2 flex items-center gap-2">
                      <span className="text-lg">🎂</span>
                      <h3 className="font-bold text-white text-sm">Yêu cầu tùy chỉnh bánh của khách</h3>
                    </div>
                    {selectedOrder.customizations.map((c) => {
                      type ZoneData = { color?: string; decoration?: string; toppings?: string[] };
                      const json = c.customization_json as {
                        size?: string;
                        flavor?: string;
                        cream_type?: string;
                        cream_color?: string;
                        topping_type?: string[];
                        special_notes?: string;
                        zones?: { top?: ZoneData; body?: ZoneData; border?: ZoneData };
                      };
                      const zones = json.zones;
                      return (
                        <div key={c.id} className="p-4 space-y-3">
                          {/* Basic specs grid */}
                          <div className="grid grid-cols-2 gap-2">
                            {json.size && (
                              <div className="bg-white rounded-lg p-2.5 border border-pink-100">
                                <p className="text-xs text-pink-500 font-medium mb-0.5">📏 Kích thước</p>
                                <p className="font-bold text-mocha text-sm">{json.size}</p>
                              </div>
                            )}
                            {json.flavor && (
                              <div className="bg-white rounded-lg p-2.5 border border-pink-100">
                                <p className="text-xs text-pink-500 font-medium mb-0.5">🍰 Hương vị</p>
                                <p className="font-bold text-mocha text-sm">{json.flavor}</p>
                              </div>
                            )}
                            {json.cream_type && (
                              <div className="bg-white rounded-lg p-2.5 border border-pink-100">
                                <p className="text-xs text-pink-500 font-medium mb-0.5">🧁 Loại kem</p>
                                <p className="font-bold text-mocha text-sm">{json.cream_type}</p>
                              </div>
                            )}
                            {json.cream_color && (
                              <div className="bg-white rounded-lg p-2.5 border border-pink-100">
                                <p className="text-xs text-pink-500 font-medium mb-0.5">🎨 Màu kem</p>
                                <div className="flex items-center gap-2">
                                  <span
                                    className="inline-block w-6 h-6 rounded-full border-2 border-pink-200 shadow-sm flex-shrink-0"
                                    style={{ backgroundColor: json.cream_color }}
                                  />
                                  <p className="font-bold text-mocha text-sm font-mono">{json.cream_color}</p>
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Toppings */}
                          {json.topping_type && json.topping_type.length > 0 && (
                            <div className="bg-white rounded-lg p-2.5 border border-pink-100">
                              <p className="text-xs text-pink-500 font-medium mb-1.5">🍓 Topping</p>
                              <div className="flex flex-wrap gap-1.5">
                                {json.topping_type.map((t, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-pink-100 text-pink-700 rounded-full text-xs font-medium">{t}</span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Zones - decoration details */}
                          {zones && (
                            <div className="space-y-2">
                              <p className="text-xs text-pink-500 font-medium">🖌️ Trang trí từng vùng bánh</p>
                              <div className="grid grid-cols-3 gap-2">
                                {(["top", "body", "border"] as const).map((zone) => {
                                  const z = zones[zone];
                                  if (!z || (!z.color && !z.decoration && (!z.toppings || z.toppings.length === 0))) return null;
                                  const zoneLabel = { top: "Mặt trên", body: "Thân bánh", border: "Viền" }[zone];
                                  return (
                                    <div key={zone} className="bg-white rounded-lg p-2 border border-pink-100 text-xs">
                                      <p className="font-semibold text-mocha mb-1">{zoneLabel}</p>
                                      {z.color && (
                                        <div className="flex items-center gap-1 mb-0.5">
                                          <span className="w-3 h-3 rounded-full border border-pink-200" style={{ backgroundColor: z.color }} />
                                          <span className="text-mocha/60 font-mono">{z.color}</span>
                                        </div>
                                      )}
                                      {z.decoration && <p className="text-mocha/70">✨ {z.decoration}</p>}
                                      {z.toppings && z.toppings.length > 0 && (
                                        <p className="text-mocha/70">🍓 {z.toppings.join(", ")}</p>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          {/* Special notes - Most prominent */}
                          {json.special_notes && (
                            <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-3">
                              <p className="text-xs font-bold text-yellow-700 mb-1 flex items-center gap-1">
                                ⚠️ Ghi chú đặc biệt của khách
                              </p>
                              <p className="text-yellow-900 font-medium text-sm whitespace-pre-wrap">{json.special_notes}</p>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </section>
                )}


                {/* AI Summary */}
                {selectedOrder.ai_summary && (
                  <section className="bg-purple-50 rounded-xl p-4">
                    <h3 className="font-semibold text-purple-800 text-sm mb-2">Tóm tắt AI</h3>
                    <p className="text-purple-700 text-sm whitespace-pre-wrap">{selectedOrder.ai_summary}</p>
                  </section>
                )}

                {/* Baker notes */}
                <section>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-mocha text-sm">Ghi chú thợ bánh</h3>
                    <span className={`text-xs ${bakerNotesInput.length > 450 ? "text-red-500" : "text-mocha/40"}`}>
                      {bakerNotesInput.length}/500
                    </span>
                  </div>
                  <textarea
                    id="baker-notes"
                    value={bakerNotesInput}
                    onChange={(e) => setBakerNotesInput(e.target.value)}
                    maxLength={500}
                    rows={3}
                    placeholder="Thêm ghi chú về quá trình làm bánh..."
                    className="w-full px-4 py-3 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 resize-none"
                  />
                  <button
                    onClick={() => handleSaveNotes(selectedOrder.id)}
                    disabled={savingNotes}
                    className="mt-2 px-4 py-2 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-50 min-h-[44px]"
                  >
                    {savingNotes ? "Đang lưu..." : "Lưu ghi chú"}
                  </button>
                </section>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </main>
  );
}

function OrderCard({
  order,
  urgency,
  onClick,
}: {
  order: BakerOrder;
  urgency: "urgent" | "soon" | "normal";
  onClick: () => void;
}) {
  const urgencyBorder = {
    urgent: "border-l-4 border-l-red-400",
    soon: "border-l-4 border-l-orange-400",
    normal: "border-l-4 border-l-green-400",
  }[urgency];

  return (
    <button
      onClick={onClick}
      className={`w-full bg-white rounded-2xl p-4 shadow-sm hover:shadow-md transition-all text-left min-h-[44px] ${urgencyBorder}`}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs text-mocha/40">
              #{order.id.slice(0, 8).toUpperCase()}
            </span>
            <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${STATUS_STYLES[order.status] || ""}`}>
              {STATUS_LABELS[order.status] || order.status}
            </span>
          </div>
          <p className="font-medium text-mocha">{order.customer_name}</p>
          <p className="text-xs text-mocha/60">{order.customer_phone}</p>
        </div>
        <div className="text-right ml-3">
          <p className="font-bold text-pink-pastel text-sm">{formatPrice(order.total_price)}</p>
          <p className="text-xs text-mocha/60 mt-1">📅 {formatDate(order.pickup_date)}</p>
        </div>
      </div>
      {order.baker_notes && (
        <p className="mt-2 text-xs text-mocha/50 truncate">
          📝 {order.baker_notes}
        </p>
      )}
    </button>
  );
}

export default function BakerDashboardPage() {
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
      <ProtectedRoute allowedRoles={["baker"]}>
        <BakerDashboardContent />
      </ProtectedRoute>
    </Suspense>
  );
}

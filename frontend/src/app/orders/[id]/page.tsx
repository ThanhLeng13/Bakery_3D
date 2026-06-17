"use client";

/**
 * Order Detail page.
 * Protected route - requires authentication.
 * Shows full order info: status timeline, pickup date, customer info,
 * items, customization details, and AI summary.
 *
 * Validates: Requirements 4.4, 4.6
 */

import { useEffect, useState, Suspense } from "react";
import { useRouter, useParams } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { apiClient } from "@/lib/api";
import type { OrderStatus, CakeDesign } from "@/types";

interface OrderItem {
  id: string;
  product_id: string | null;
  size: string;
  flavor: string;
  quantity: number;
  unit_price: number;
}

interface StatusHistoryEntry {
  old_status: OrderStatus | null;
  new_status: OrderStatus;
  changed_at: string;
  changed_by: string | null;
}

interface OrderDetail {
  id: string;
  status: OrderStatus;
  total_price: number;
  pickup_date: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string | null;
  ai_summary: string | null;
  baker_notes: string | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  customizations: Array<{
    id: string;
    order_item_id: string | null;
    customization_json: CakeDesign;
    preview_image_url: string | null;
    created_at: string;
  }>;
  status_history: StatusHistoryEntry[];
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

const STATUS_ORDER: OrderStatus[] = [
  "pending",
  "confirmed",
  "in_production",
  "ready",
  "delivered",
];

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN").format(price) + "đ";
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("vi-VN", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatShortDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ReviewForm component for delivered orders
function ReviewForm({ orderId, items }: { orderId: string; items: OrderItem[] }) {
  const [selectedProductId, setSelectedProductId] = useState<string>(
    items.find((i) => i.product_id)?.product_id || ""
  );
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [hoverRating, setHoverRating] = useState(0);

  const reviewableItems = items.filter((i) => i.product_id);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (rating === 0) {
      setError("Vui lòng chọn số sao đánh giá");
      return;
    }
    if (!selectedProductId) {
      setError("Vui lòng chọn sản phẩm cần đánh giá");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await apiClient.post("/api/v1/reviews", {
        product_id: selectedProductId,
        order_id: orderId,
        rating,
        comment: comment.trim() || null,
      });
      setSubmitted(true);
    } catch (err: unknown) {
      const apiErr = err as { detail?: string | { msg: string }[] };
      let errorMsg = "Gửi đánh giá thất bại. Vui lòng thử lại.";
      if (typeof apiErr?.detail === "string") {
        errorMsg = apiErr.detail === "Bạn đã đánh giá sản phẩm này cho đơn hàng này rồi."
          ? "Bạn đã đánh giá sản phẩm này rồi."
          : apiErr.detail;
      } else if (Array.isArray(apiErr?.detail)) {
        errorMsg = apiErr.detail[0]?.msg || errorMsg;
      }
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
        <div className="text-center py-4">
          <div className="text-4xl mb-3">⭐</div>
          <h2 className="font-heading text-lg font-bold text-mocha mb-1">Cảm ơn bạn đã đánh giá!</h2>
          <p className="text-mocha/60 text-sm">Đánh giá của bạn giúp chúng tôi phát triển tốt hơn.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
      <h2 className="font-heading text-lg font-bold text-mocha mb-4">
        Đánh giá sản phẩm
      </h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Product selector (if multiple items) */}
        {reviewableItems.length > 1 && (
          <div>
            <label className="block text-sm font-medium text-mocha mb-1">Chọn sản phẩm</label>
            <select
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px]"
            >
              {reviewableItems.map((item) => (
                <option key={item.id} value={item.product_id!}>
                  Bánh kem {item.size} - {item.flavor}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Star rating */}
        <div>
          <label className="block text-sm font-medium text-mocha mb-2">Đánh giá <span className="text-red-500">*</span></label>
          <div className="flex gap-1" role="group" aria-label="Chọn số sao">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setRating(star)}
                onMouseEnter={() => setHoverRating(star)}
                onMouseLeave={() => setHoverRating(0)}
                className="text-3xl transition-transform hover:scale-110 min-w-[44px] min-h-[44px] flex items-center justify-center"
                aria-label={`${star} sao`}
              >
                {star <= (hoverRating || rating) ? "⭐" : "☆"}
              </button>
            ))}
          </div>
          {rating > 0 && (
            <p className="text-sm text-mocha/60 mt-1">
              {["", "Rất tệ", "Tệ", "Bình thường", "Tốt", "Xuất sắc"][rating]}
            </p>
          )}
        </div>

        {/* Comment */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label htmlFor="review-comment" className="text-sm font-medium text-mocha">
              Nhận xét <span className="text-mocha/50">(không bắt buộc)</span>
            </label>
            <span className={`text-xs ${comment.length > 900 ? "text-red-500" : "text-mocha/40"}`}>
              {comment.length}/1000
            </span>
          </div>
          <textarea
            id="review-comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="Chia sẻ cảm nhận của bạn về bánh..."
            className="w-full px-4 py-3 rounded-xl border border-mocha/20 text-sm text-mocha bg-cream/50 placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={submitting || rating === 0}
          className="w-full py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
        >
          {submitting ? "Đang gửi..." : "Gửi đánh giá"}
        </button>
      </form>
    </section>
  );
}

function OrderDetailContent() {
  const router = useRouter();
  const params = useParams();
  const orderId = params.id as string;

  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reordering, setReordering] = useState(false);

  useEffect(() => {
    async function fetchOrder() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get<OrderDetail>(
          `/api/v1/orders/${orderId}`
        );
        setOrder(data);
      } catch {
        setError("Không thể tải thông tin đơn hàng. Vui lòng thử lại sau.");
      } finally {
        setLoading(false);
      }
    }

    if (orderId) {
      fetchOrder();
    }
  }, [orderId]);

  function handleReorder() {
    if (!order) return;
    setReordering(true);
    const reorderData = {
      fromOrderId: order.id,
      items: order.items.map((item) => ({
        product_id: item.product_id,
        size: item.size,
        flavor: item.flavor,
        quantity: item.quantity,
        unit_price: item.unit_price,
      })),
      customizations: (order.customizations ?? []).map((c) => c.customization_json),
      customer_name: order.customer_name,
      customer_phone: order.customer_phone,
      customer_email: order.customer_email,
    };
    try {
      sessionStorage.setItem("reorder_data", JSON.stringify(reorderData));
    } catch {
      // sessionStorage might be unavailable in some contexts
    }
    router.push("/cake-builder?reorder=1");
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-cream">
        <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-30">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
            <div className="w-6 h-6 bg-mocha/10 rounded animate-pulse" />
            <div className="h-6 bg-mocha/10 rounded w-40 animate-pulse" />
          </div>
        </header>
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-4">
          <div className="bg-white rounded-2xl p-6 animate-pulse">
            <div className="h-6 bg-mocha/10 rounded w-48 mb-4" />
            <div className="h-4 bg-mocha/10 rounded w-full mb-2" />
            <div className="h-4 bg-mocha/10 rounded w-3/4" />
          </div>
        </div>
      </main>
    );
  }

  if (error || !order) {
    return (
      <main className="min-h-screen bg-cream flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-mocha/70 mb-4">{error || "Không tìm thấy đơn hàng"}</p>
          <button
            onClick={() => router.push("/orders")}
            className="px-6 py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
          >
            Quay lại danh sách
          </button>
        </div>
      </main>
    );
  }

  const currentStatusIndex = STATUS_ORDER.indexOf(order.status);

  return (
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/orders")}
              className="text-mocha hover:text-pink-pastel transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Quay lại"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
            <div>
              <h1 className="font-heading text-lg md:text-xl text-mocha font-bold">
                Chi tiết đơn hàng
              </h1>
              <p className="text-xs text-mocha/50 font-mono">
                #{order.id.slice(0, 8).toUpperCase()}
              </p>
            </div>
          </div>
          {/* Re-order Button */}
          <button
            onClick={handleReorder}
            disabled={reordering}
            id="reorder-btn"
            className="flex items-center gap-2 px-4 py-2 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-50 min-h-[44px] flex-shrink-0"
          >
            {reordering ? (
              <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M23 4v6h-6M1 20v-6h6" />
                <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
              </svg>
            )}
            <span className="hidden sm:inline">Đặt lại đơn này</span>
          </button>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {/* Status Badge + Timeline */}
        <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-heading text-lg font-bold text-mocha">
              Trạng thái
            </h2>
            <span
              className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_STYLES[order.status]}`}
            >
              {STATUS_LABELS[order.status]}
            </span>
          </div>

          {/* Status Timeline */}
          <div className="flex items-center justify-between relative">
            {/* Progress bar background */}
            <div className="absolute top-4 left-0 right-0 h-0.5 bg-mocha/10" />
            {/* Progress bar filled */}
            <div
              className="absolute top-4 left-0 h-0.5 bg-pink-pastel transition-all duration-500"
              style={{
                width: `${(currentStatusIndex / (STATUS_ORDER.length - 1)) * 100}%`,
              }}
            />

            {STATUS_ORDER.map((status, index) => {
              const isCompleted = index <= currentStatusIndex;
              const isCurrent = index === currentStatusIndex;
              return (
                <div
                  key={status}
                  className="relative flex flex-col items-center z-10"
                >
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                      isCurrent
                        ? "bg-pink-pastel text-white ring-4 ring-pink-pastel/20"
                        : isCompleted
                          ? "bg-pink-pastel text-white"
                          : "bg-white border-2 border-mocha/20 text-mocha/40"
                    }`}
                  >
                    {isCompleted ? "✓" : index + 1}
                  </div>
                  <span
                    className={`mt-2 text-[10px] md:text-xs text-center max-w-[60px] ${
                      isCurrent ? "text-pink-pastel font-medium" : "text-mocha/50"
                    }`}
                  >
                    {STATUS_LABELS[status]}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Order Info */}
        <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
          <h2 className="font-heading text-lg font-bold text-mocha mb-4">
            Thông tin đơn hàng
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-mocha/70 text-sm">Ngày nhận bánh</span>
              <span className="font-medium text-mocha text-sm">
                {formatDate(order.pickup_date)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-mocha/70 text-sm">Ngày đặt</span>
              <span className="text-mocha text-sm">
                {formatDate(order.created_at)}
              </span>
            </div>
            <div className="flex justify-between items-center pt-3 border-t border-mocha/10">
              <span className="font-medium text-mocha">Tổng tiền</span>
              <span className="font-bold text-pink-pastel text-xl">
                {formatPrice(order.total_price)}
              </span>
            </div>
          </div>
        </section>

        {/* Customer Info */}
        <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
          <h2 className="font-heading text-lg font-bold text-mocha mb-4">
            Thông tin khách hàng
          </h2>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-mocha/70 text-sm">Họ tên</span>
              <span className="text-mocha text-sm font-medium">{order.customer_name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-mocha/70 text-sm">Điện thoại</span>
              <span className="text-mocha text-sm">{order.customer_phone}</span>
            </div>
            {order.customer_email && (
              <div className="flex justify-between">
                <span className="text-mocha/70 text-sm">Email</span>
                <span className="text-mocha text-sm">{order.customer_email}</span>
              </div>
            )}
          </div>
        </section>

        {/* Items */}
        <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
          <h2 className="font-heading text-lg font-bold text-mocha mb-4">
            Sản phẩm
          </h2>
          <div className="space-y-3">
            {order.items.map((item) => (
              <div
                key={item.id}
                className="flex justify-between items-center py-2 border-b border-mocha/5 last:border-0"
              >
                <div>
                  <p className="text-mocha text-sm font-medium">
                    Bánh kem {item.size}
                  </p>
                  <p className="text-mocha/60 text-xs">
                    {item.flavor} × {item.quantity}
                  </p>
                </div>
                <span className="text-mocha font-medium text-sm">
                  {formatPrice(item.unit_price * item.quantity)}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Customization Details */}
        {order.customizations && order.customizations.length > 0 && (
          <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
            <h2 className="font-heading text-lg font-bold text-mocha mb-4">
              Chi tiết tùy chỉnh
            </h2>
            {order.customizations.map((customization, idx) => (
              <div key={idx} className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-mocha/70">Kích thước</span>
                  <span className="text-mocha font-medium">
                    {customization.customization_json.size}
                  </span>
                </div>
                {customization.customization_json.flavor && (
                  <div className="flex justify-between">
                    <span className="text-mocha/70">Hương vị</span>
                    <span className="text-mocha font-medium">
                      {customization.customization_json.flavor}
                    </span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-mocha/70">Loại kem</span>
                  <span className="text-mocha font-medium">
                    {customization.customization_json.cream_type}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70">Màu kem</span>
                  <div className="flex items-center gap-2">
                    <span
                      className="w-4 h-4 rounded-full border border-mocha/20"
                      style={{ backgroundColor: customization.customization_json.cream_color }}
                    />
                    <span className="text-mocha font-medium">
                      {customization.customization_json.cream_color}
                    </span>
                  </div>
                </div>
                {customization.customization_json.topping_type && (
                  <div className="flex justify-between">
                    <span className="text-mocha/70">Topping</span>
                    <span className="text-mocha font-medium">
                      {customization.customization_json.topping_type}
                    </span>
                  </div>
                )}
                {customization.customization_json.special_notes && (
                  <div className="pt-2 border-t border-mocha/10">
                    <span className="text-mocha/70 block mb-1">Ghi chú đặc biệt</span>
                    <p className="text-mocha">
                      {customization.customization_json.special_notes}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </section>
        )}

        {/* AI Summary */}
        {order.ai_summary && (
          <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
            <h2 className="font-heading text-lg font-bold text-mocha mb-4">
              Tóm tắt AI
            </h2>
            <p className="text-mocha text-sm whitespace-pre-wrap leading-relaxed">
              {order.ai_summary}
            </p>
          </section>
        )}

        {/* Baker Notes */}
        {order.baker_notes && (
          <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
            <h2 className="font-heading text-lg font-bold text-mocha mb-4">
              Ghi chú thợ bánh
            </h2>
            <p className="text-mocha text-sm whitespace-pre-wrap leading-relaxed">
              {order.baker_notes}
            </p>
          </section>
        )}

        {/* Status History */}
        {order.status_history && order.status_history.length > 0 && (
          <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
            <h2 className="font-heading text-lg font-bold text-mocha mb-4">
              Lịch sử trạng thái
            </h2>
            <div className="space-y-3">
              {order.status_history.map((entry, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-3 text-sm"
                >
                  <div className="w-2 h-2 rounded-full bg-pink-pastel flex-shrink-0" />
                  <div className="flex-1">
                    <span className="text-mocha font-medium">
                      {STATUS_LABELS[entry.new_status]}
                    </span>
                  </div>
                  <span className="text-mocha/50 text-xs">
                    {formatShortDate(entry.changed_at)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Review Form - only for delivered orders within 30 days */}
        {order.status === "delivered" && (() => {
          const deliveredAt = new Date(order.updated_at);
          const now = new Date();
          const daysSince = (now.getTime() - deliveredAt.getTime()) / (1000 * 60 * 60 * 24);
          return daysSince <= 30;
        })() && (
          <ReviewForm
            orderId={order.id}
            items={order.items}
          />
        )}

        {/* Back button */}
        <button
          onClick={() => router.push("/orders")}
          className="w-full py-3 bg-white text-mocha border border-mocha/20 rounded-full font-medium hover:bg-cream transition-colors min-h-[44px]"
        >
          Quay lại
        </button>
      </div>
    </main>
  );
}


export default function OrderDetailPage() {
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
        <OrderDetailContent />
      </ProtectedRoute>
    </Suspense>
  );
}

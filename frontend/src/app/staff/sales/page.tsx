"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, type ApiError } from "@/lib/api";
import type { OrderStatus } from "@/types";

interface SalesOrder {
  id: string;
  status: "pending" | "ready";
  total_price: number;
  pickup_date: string;
  customer_name: string;
  customer_phone: string;
  customer_email?: string | null;
  created_at: string;
}

interface SalesQueueResponse {
  orders: SalesOrder[];
  total: number;
  pending_count: number;
  ready_count: number;
}

interface SalesOrderDetail extends SalesOrder {
  items: Array<{
    id: string;
    size?: string | null;
    flavor?: string | null;
    quantity: number;
    unit_price: number;
  }>;
  ai_summary?: string | null;
  baker_notes?: string | null;
}

const STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Chờ xác nhận",
  confirmed: "Đã xác nhận",
  in_production: "Đang làm",
  ready: "Chờ khách nhận",
  delivered: "Đã giao",
};

function formatPrice(value: number) {
  return new Intl.NumberFormat("vi-VN").format(value) + "đ";
}

function formatDate(value: string) {
  return new Date(value).toLocaleString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function errorMessage(error: unknown): string {
  const detail = (error as ApiError)?.detail;
  return typeof detail === "string" ? detail : "Không thể thực hiện thao tác. Vui lòng thử lại.";
}

export default function StaffSalesPage() {
  const [queue, setQueue] = useState<SalesQueueResponse | null>(null);
  const [selected, setSelected] = useState<SalesOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setQueue(await apiClient.get<SalesQueueResponse>("/api/v1/staff/orders"));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // Guards against out-of-order detail responses. Staff can tap order A then
  // order B before A resolves; without this, A's late response would overwrite
  // the newer selection and a subsequent completeStep would target the wrong
  // order. Each request takes a ticket and only the newest one may write state.
  const detailRequestRef = useRef(0);

  async function openDetail(orderId: string) {
    const requestId = ++detailRequestRef.current;
    // Clear the previous order immediately so the panel never shows stale data
    // while the new one loads.
    setSelected(null);
    setDetailLoading(true);
    setError("");
    try {
      const detail = await apiClient.get<SalesOrderDetail>(
        `/api/v1/staff/orders/${orderId}`,
      );
      if (requestId !== detailRequestRef.current) return; // superseded
      setSelected(detail);
    } catch (err) {
      if (requestId !== detailRequestRef.current) return; // superseded
      setError(errorMessage(err));
    } finally {
      if (requestId === detailRequestRef.current) {
        setDetailLoading(false);
      }
    }
  }

  /** Close the detail panel and invalidate any in-flight request. */
  function closeDetail() {
    detailRequestRef.current += 1;
    setSelected(null);
    setDetailLoading(false);
  }

  async function completeStep(order: SalesOrderDetail) {
    const nextStatus = order.status === "pending" ? "confirmed" : "delivered";
    setUpdating(true);
    setError("");
    try {
      await apiClient.patch(`/api/v1/staff/orders/${order.id}/status`, {
        status: nextStatus,
      });
      closeDetail();
      await loadQueue();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUpdating(false);
    }
  }

  const pendingOrders = queue?.orders.filter((order) => order.status === "pending") ?? [];
  const readyOrders = queue?.orders.filter((order) => order.status === "ready") ?? [];

  return (
    <main className="mx-auto max-w-7xl px-4 py-6">
      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        <SummaryCard label="Cần xử lý" value={queue?.total ?? 0} color="text-ink" />
        <SummaryCard label="Chờ xác nhận" value={queue?.pending_count ?? 0} color="text-ink" />
        <SummaryCard label="Chờ khách nhận" value={queue?.ready_count ?? 0} color="text-green-700" />
      </section>

      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="font-heading text-2xl font-bold text-ink">Đơn cần bán hàng xử lý</h2>
          <p className="mt-1 text-sm text-muted">Xác nhận đơn mới và bàn giao bánh đã hoàn thành.</p>
        </div>
        <button
          onClick={loadQueue}
          disabled={loading}
          className="min-h-[42px] rounded-full border border-line bg-white px-4 text-sm font-medium text-ink hover:bg-surface disabled:opacity-50"
        >
          Làm mới
        </button>
      </div>

      {error && (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
      )}

      {loading ? (
        <div className="rounded-2xl bg-white p-10 text-center text-muted">Đang tải hàng đợi...</div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          <OrderColumn
            title="Đơn mới chờ xác nhận"
            emptyText="Không có đơn mới."
            orders={pendingOrders}
            onOpen={openDetail}
          />
          <OrderColumn
            title="Bánh sẵn sàng giao khách"
            emptyText="Không có bánh chờ giao."
            orders={readyOrders}
            onOpen={openDetail}
          />
        </div>
      )}

      {(selected || detailLoading) && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-ink/50 p-4 backdrop-blur-sm">
          <div className="my-8 w-full max-w-xl rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-line p-5">
              <h3 className="font-heading text-lg font-bold text-ink">Chi tiết bán hàng</h3>
              <button
                onClick={closeDetail}
                className="min-h-[40px] min-w-[40px] rounded-full text-xl text-muted hover:bg-surface"
                aria-label="Đóng"
              >
                ×
              </button>
            </div>
            {detailLoading ? (
              <div className="p-10 text-center text-muted">Đang tải chi tiết...</div>
            ) : selected ? (
              <div className="space-y-5 p-5">
                <div className="grid grid-cols-2 gap-3 rounded-xl bg-surface p-4 text-sm">
                  <Info label="Khách hàng" value={selected.customer_name} />
                  <Info label="Điện thoại" value={selected.customer_phone} />
                  <Info label="Ngày nhận" value={formatDate(selected.pickup_date)} />
                  <Info label="Tổng tiền" value={formatPrice(selected.total_price)} strong />
                </div>

                <div>
                  <h4 className="mb-2 text-sm font-semibold text-ink">Sản phẩm</h4>
                  <div className="space-y-2">
                    {selected.items.map((item) => (
                      <div key={item.id} className="flex justify-between rounded-xl border border-line p-3 text-sm">
                        <span className="text-ink">
                          Bánh {item.size || "theo mẫu"} · {item.flavor || "hương vị đã chọn"} × {item.quantity}
                        </span>
                        <span className="font-semibold text-ink">{formatPrice(item.unit_price * item.quantity)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {selected.baker_notes && (
                  <div className="rounded-xl bg-subtle p-4 text-sm text-ink">
                    <strong>Ghi chú thợ bánh:</strong> {selected.baker_notes}
                  </div>
                )}

                <button
                  onClick={() => completeStep(selected)}
                  disabled={updating}
                  className="w-full min-h-[48px] rounded-xl bg-action px-4 font-semibold text-white hover:bg-brand-soft hover:text-white disabled:opacity-50"
                >
                  {updating
                    ? "Đang cập nhật..."
                    : selected.status === "pending"
                      ? "Xác nhận nhận đơn"
                      : "Xác nhận đã giao và thu tiền"}
                </button>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </main>
  );
}

function SummaryCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div className="rounded-2xl border border-line bg-white p-5 shadow-sm">
      <p className="text-sm text-muted">{label}</p>
      <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function OrderColumn({
  title,
  emptyText,
  orders,
  onOpen,
}: {
  title: string;
  emptyText: string;
  orders: SalesOrder[];
  onOpen: (id: string) => void;
}) {
  return (
    <section className="rounded-2xl border border-line bg-white p-4 shadow-sm">
      <h3 className="mb-4 font-semibold text-ink">{title} ({orders.length})</h3>
      {orders.length === 0 ? (
        <p className="rounded-xl bg-surface p-6 text-center text-sm text-muted">{emptyText}</p>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => (
            <button
              key={order.id}
              onClick={() => onOpen(order.id)}
              className="w-full rounded-xl border border-line p-4 text-left transition-colors hover:border-line hover:bg-subtle"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-ink">{order.customer_name}</p>
                  <p className="mt-0.5 text-xs text-muted">{order.customer_phone}</p>
                </div>
                <span className="rounded-full bg-surface px-2.5 py-1 text-xs font-medium text-ink">
                  {STATUS_LABELS[order.status]}
                </span>
              </div>
              <div className="mt-3 flex items-end justify-between text-sm">
                <span className="text-muted">Nhận: {formatDate(order.pickup_date)}</span>
                <span className="font-bold text-ink">{formatPrice(order.total_price)}</span>
              </div>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function Info({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className={strong ? "font-bold text-ink" : "font-medium text-ink"}>{value}</p>
    </div>
  );
}

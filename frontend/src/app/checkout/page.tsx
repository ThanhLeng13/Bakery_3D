"use client";

/**
 * Checkout / Order Form page.
 * Protected route - requires authentication.
 *
 * Supports two modes:
 * 1. Cart mode    — items come from CartContext (products added via "Thêm vào giỏ")
 * 2. Builder mode — single cake design from localStorage (Cake Builder flow)
 *
 * Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.7
 */

import { useState, useEffect, useMemo, Suspense } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthContext } from "@/contexts/AuthContext";
import { useCart } from "@/contexts/CartContext";
import { apiClient } from "@/lib/api";
import type { CakeDesign, CakeSize } from "@/types";

interface OrderConfirmation {
  /** Cake order mode returns "id", sweet purchase mode returns "purchase_id" */
  id?: string;
  purchase_id?: string;
  total_price: number;
  pickup_date?: string;      // only for cake orders
  created_at?: string;       // only for sweet purchases
  status: string;
  message?: string;          // only for sweet purchases
}

interface FormErrors {
  full_name?: string;
  phone?: string;
  email?: string;
  pickup_date?: string;
  branch?: string;   // lỗi chi nhánh khi isCartMode
  general?: string;
}

// Price map by size (for Cake Builder mode only)
const SIZE_PRICES: Record<CakeSize, number> = {
  "16cm": 250000,
  "20cm": 350000,
  "24cm": 450000,
  "2-tier": 650000,
};

const SIZE_LABELS: Record<CakeSize, string> = {
  "16cm": "16cm (4-6 người)",
  "20cm": "20cm (8-10 người)",
  "24cm": "24cm (12-15 người)",
  "2-tier": "2 tầng (20+ người)",
};

function getMinPickupDate(hasTwoTier: boolean): Date {
  const now = new Date();
  const hoursAhead = hasTwoTier ? 48 : 24;
  return new Date(now.getTime() + hoursAhead * 60 * 60 * 1000);
}

function getMaxPickupDate(): Date {
  const now = new Date();
  return new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
}

function formatDateForInput(date: Date): string {
  return date.toISOString().slice(0, 16);
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN").format(price) + "đ";
}

function formatDisplayDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("vi-VN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CheckoutContent() {
  const router = useRouter();
  const { user } = useAuthContext();
  const { items: cartItems, clearCart, selectedBranchId, selectedBranchName } = useCart();

  // Builder mode: load from localStorage
  const [cakeDesign, setCakeDesign] = useState<CakeDesign | null>(null);

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [pickupDate, setPickupDate] = useState("");
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmation, setConfirmation] = useState<OrderConfirmation | null>(null);
  // Persisted at submit time so confirmation screen shows correct info even after clearCart()
  const [submittedIsCartMode, setSubmittedIsCartMode] = useState(false);
  const [submittedBranchName, setSubmittedBranchName] = useState<string | null>(null);

  // Determine mode
  const isCartMode = cartItems.length > 0;   // sweet products
  const isCakeMode = !isCartMode;            // cake builder

  // Load Cake Builder design only when cart is empty
  useEffect(() => {
    if (isCartMode) return; // Cart mode takes priority
    try {
      const stored = localStorage.getItem("cake_customization_json");
      if (stored) {
        const design = JSON.parse(stored) as CakeDesign;
        setCakeDesign(design);
      }
    } catch {
      // Invalid data in localStorage
    }
  }, [isCartMode]);

  // Pre-fill user info
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      if (user.phone) setPhone(user.phone);
      if (user.email) setEmail(user.email);
    }
  }, [user]);

  // Calculate totals
  const builderTotal = useMemo(() => {
    if (!cakeDesign) return 0;
    return SIZE_PRICES[cakeDesign.size] || 350000;
  }, [cakeDesign]);

  const cartTotal = useMemo(
    () => cartItems.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0),
    [cartItems]
  );

  const totalPrice = isCartMode ? cartTotal : builderTotal;

  // hasTwoTier only applies to cake builder mode
  const hasTwoTier = isCakeMode && cakeDesign?.size === "2-tier";

  const minDate = useMemo(() => getMinPickupDate(!!hasTwoTier), [hasTwoTier]);
  const maxDate = useMemo(() => getMaxPickupDate(), []);

  function validateForm(): boolean {
    const newErrors: FormErrors = {};

    if (!fullName.trim()) {
      newErrors.full_name = "Vui lòng nhập họ tên";
    }

    if (!phone.trim()) {
      newErrors.phone = "Vui lòng nhập số điện thoại";
    } else if (!/^\d{10}$/.test(phone.trim())) {
      newErrors.phone = "Số điện thoại phải có 10 chữ số";
    }

    if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      newErrors.email = "Email không hợp lệ";
    }

    // Pickup date is only required for cake orders (not sweet purchase)
    if (isCakeMode) {
      if (!pickupDate) {
        newErrors.pickup_date = "Vui lòng chọn ngày nhận bánh";
      } else {
        const selectedDate = new Date(pickupDate);
        if (selectedDate < minDate) {
          const hours = hasTwoTier ? 48 : 24;
          newErrors.pickup_date = `Ngày nhận phải cách ít nhất ${hours} giờ từ bây giờ`;
        } else if (selectedDate > maxDate) {
          newErrors.pickup_date = "Ngày nhận không được quá 30 ngày kể từ hôm nay";
        }
      }
    }

    // branch_id required for sweet purchases (must pick up from a specific branch)
    if (isCartMode && !selectedBranchId) {
      newErrors.branch = "Vui lòng chọn chi nhánh nhận bánh";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!validateForm()) return;
    if (isCakeMode && !cakeDesign) return;

    setSubmitting(true);
    setErrors({});

    try {
      if (isCartMode) {
        // ====== SWEET PURCHASE MODE ======
        // POST /api/v1/purchases — trừ stock ngay, thanh toán offline
        const purchaseData = {
          items: cartItems.map((item) => ({
            product_id: item.productId,
            quantity: item.quantity,
          })),
          customer_name: fullName.trim(),
          customer_phone: phone.trim(),
          notes: null,
          branch_id: selectedBranchId!, // guaranteed non-null by validateForm
        };

        const response = await apiClient.post<OrderConfirmation>(
          "/api/v1/purchases",
          purchaseData
        );
        // Persist mode/branch BEFORE clearCart() so confirmation screen is correct
        setSubmittedIsCartMode(true);
        setSubmittedBranchName(selectedBranchName ?? null);
        setConfirmation(response);
        clearCart();

      } else {
        // ====== CAKE ORDER MODE ======
        // POST /api/v1/orders — đặt bánh kem theo yêu cầu
        const orderItems = [
          {
            product_id: "00000000-0000-0000-0000-000000000000",
            size: cakeDesign!.size,
            flavor: cakeDesign!.flavor || "Vani",
            quantity: 1,
            unit_price: builderTotal,
            customization_json: cakeDesign,
          },
        ];

        const orderData = {
          full_name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim() || null,
          pickup_date: new Date(pickupDate).toISOString(),
          items: orderItems,
          ai_summary: null,
        };

        const response = await apiClient.post<OrderConfirmation>(
          "/api/v1/orders",
          orderData
        );
        setConfirmation(response);
        localStorage.removeItem("cake_customization_json");
      }

    } catch (err: unknown) {
      const apiErr = err as { detail?: string | Array<{ field: string; message: string; loc?: string[] }> };
      if (apiErr?.detail) {
        if (typeof apiErr.detail === "string") {
          setErrors({ general: apiErr.detail });
        } else if (Array.isArray(apiErr.detail)) {
          const fieldErrors: FormErrors = {};
          apiErr.detail.forEach((e) => {
            const field = e.field || (e.loc ? e.loc[e.loc.length - 1] : "");
            if (field === "full_name") fieldErrors.full_name = e.message || "Trường bắt buộc";
            else if (field === "phone") fieldErrors.phone = e.message || "Trường bắt buộc";
            else if (field === "email") fieldErrors.email = e.message || "Email không hợp lệ";
            else if (field === "pickup_date") fieldErrors.pickup_date = e.message || "Ngày không hợp lệ";
            else fieldErrors.general = e.message || "Đã xảy ra lỗi";
          });
          setErrors(fieldErrors);
        }
      } else {
        setErrors({ general: "Đã xảy ra lỗi, vui lòng thử lại sau" });
      }
    } finally {
      setSubmitting(false);
    }
  }

  // No items at all (cart empty + no builder design)
  if (!isCartMode && !cakeDesign) {
    return (
      <main className="min-h-screen bg-cream flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-5 bg-pink-pastel/10 rounded-full flex items-center justify-center">
            <svg className="w-10 h-10 text-pink-pastel/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
            </svg>
          </div>
          <h2 className="font-heading text-xl text-mocha font-bold mb-2">
            Giỏ hàng trống
          </h2>
          <p className="text-mocha/70 mb-6">
            Hãy thêm sản phẩm vào giỏ hoặc thiết kế bánh của bạn trước.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={() => router.push("/products")}
              className="px-6 py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
            >
              Xem sản phẩm
            </button>
            <button
              onClick={() => router.push("/cake-builder")}
              className="px-6 py-3 bg-white text-mocha border border-mocha/20 rounded-full font-medium hover:bg-cream transition-colors min-h-[44px]"
            >
              Thiết kế bánh
            </button>
          </div>
        </div>
      </main>
    );
  }

  // Order confirmation view
  if (confirmation) {
    return (
      <main className="min-h-screen bg-cream">
        <div className="max-w-2xl mx-auto px-4 py-8">
          <div className="bg-white rounded-2xl shadow-sm p-6 md:p-8 text-center">
            {/* Success icon */}
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>

            <h1 className="font-heading text-2xl md:text-3xl font-bold text-mocha mb-2">
              {submittedIsCartMode ? "Mua hàng thành công!" : "Đặt hàng thành công!"}
            </h1>
            <p className="text-mocha/70 mb-6">
              {submittedIsCartMode
                ? "Cảm ơn bạn đã mua hàng. Vui lòng đến quán thanh toán và nhận bánh."
                : "Cảm ơn bạn đã đặt hàng. Chúng tôi sẽ xác nhận đơn hàng sớm nhất."}
            </p>

            {/* Order details */}
            <div className="bg-cream rounded-xl p-4 md:p-6 text-left space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-mocha/70 text-sm">Mã đơn hàng</span>
                <span className="font-medium text-mocha text-sm font-mono">
                  #{(confirmation.id || confirmation.purchase_id || "").slice(0, 8).toUpperCase()}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-mocha/70 text-sm">Tổng tiền</span>
                <span className="font-bold text-pink-pastel text-lg">
                  {formatPrice(confirmation.total_price)}
                </span>
              </div>
              {confirmation.pickup_date ? (
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70 text-sm">Ngày nhận bánh</span>
                  <span className="font-medium text-mocha text-sm">
                    {formatDisplayDate(confirmation.pickup_date)}
                  </span>
                </div>
              ) : confirmation.created_at ? (
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70 text-sm">Ngày mua hàng</span>
                  <span className="font-medium text-mocha text-sm">
                    {formatDisplayDate(confirmation.created_at)}
                  </span>
                </div>
              ) : null}
              {submittedIsCartMode && submittedBranchName && (
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70 text-sm">Chi nhánh nhận</span>
                  <span className="font-medium text-mocha text-sm">{submittedBranchName}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-mocha/70 text-sm">Trạng thái</span>
                <span className={`px-3 py-1 text-xs font-medium rounded-full ${
                  confirmation.status === "completed" 
                    ? "bg-green-100 text-green-800" 
                    : "bg-yellow-100 text-yellow-800"
                }`}>
                  {confirmation.status === "completed" ? "Đã hoàn thành" : "Chờ xác nhận"}
                </span>
              </div>
            </div>


            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 mt-6">
              <button
                onClick={() => router.push("/orders")}
                className="flex-1 px-6 py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
              >
                Xem đơn hàng
              </button>
              <button
                onClick={() => router.push("/")}
                className="flex-1 px-6 py-3 bg-white text-mocha border border-mocha/20 rounded-full font-medium hover:bg-cream transition-colors min-h-[44px]"
              >
                Về trang chủ
              </button>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // ——— Order Form ———
  return (
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.back()}
            className="text-mocha hover:text-pink-pastel transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Quay lại"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <button
            onClick={() => router.push("/")}
            className="font-heading text-lg text-mocha font-bold flex items-center gap-1.5 hover:text-pink-pastel transition-colors"
            title="Về trang chủ"
          >
            🎂 <span className="hidden sm:inline">Bơ Nơ</span>
          </button>
          <span className="text-mocha/20">|</span>
          <h1 className="font-heading text-xl md:text-2xl text-mocha font-bold">
            Thanh toán
          </h1>
          {isCartMode && (
            <span className="ml-auto text-sm text-mocha/60">
              {cartItems.reduce((s, i) => s + i.quantity, 0)} sản phẩm
            </span>
          )}
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* General error */}
          {errors.general && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm">
              {errors.general}
            </div>
          )}

          {/* ─── CART MODE: Product list ─── */}
          {isCartMode && (
            <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
              <h2 className="font-heading text-lg font-bold text-mocha mb-1">
                Sản phẩm đã chọn
              </h2>
              {selectedBranchName ? (
                <p className="text-sm text-mocha/60 mb-4 flex items-center gap-1.5">
                  <svg className="w-3.5 h-3.5 text-pink-pastel flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Nhận tại: <span className="font-medium text-mocha">{selectedBranchName}</span>
                </p>
              ) : (
                <p className="text-sm text-red-500 mb-4 flex items-center gap-1.5">
                  ⚠️ Vui lòng quay lại trang sản phẩm và chọn chi nhánh nhận bánh trước khi thanh toán.
                </p>
              )}
              {errors.branch && (
                <p className="text-sm text-red-500 mb-3">{errors.branch}</p>
              )}
              <div className="space-y-3">
                {cartItems.map((item) => (
                  <div key={item.cartKey} className="flex gap-3 p-3 bg-cream/60 rounded-xl">
                    {/* Thumbnail */}
                    <div className="w-14 h-14 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100 relative">
                      {item.imageUrl ? (
                        <Image
                          src={item.imageUrl}
                          alt={item.productName}
                          fill
                          sizes="56px"
                          className="object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <svg className="w-6 h-6 text-mocha/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-2.21 0-4 1.79-4 4h8c0-2.21-1.79-4-4-4z" />
                          </svg>
                        </div>
                      )}
                    </div>
                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-mocha text-sm truncate">{item.productName}</p>
                      <div className="flex flex-wrap gap-x-2 text-xs text-mocha/55 mt-0.5">
                        {item.expiresAt && <span className="text-amber-600">HSD: {item.expiresAt.split("T")[0].split("-").reverse().join("/")}</span>}
                        <span>• SL: {item.quantity}</span>
                      </div>
                    </div>
                    {/* Price */}
                    <div className="text-right">
                      <p className="font-semibold text-pink-pastel text-sm">{formatPrice(item.unitPrice * item.quantity)}</p>
                      {item.quantity > 1 && (
                        <p className="text-xs text-mocha/40">{formatPrice(item.unitPrice)} × {item.quantity}</p>
                      )}
                    </div>
                  </div>
                ))}

                {/* Cart total */}
                <div className="pt-3 border-t border-mocha/10 flex justify-between items-center">
                  <span className="font-medium text-mocha">Tổng cộng</span>
                  <span className="font-bold text-pink-pastel text-xl">{formatPrice(totalPrice)}</span>
                </div>
              </div>
            </section>
          )}

          {/* ─── BUILDER MODE: Cake summary ─── */}
          {!isCartMode && cakeDesign && (
            <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
              <h2 className="font-heading text-lg font-bold text-mocha mb-4">
                Tóm tắt sản phẩm
              </h2>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70 text-sm">Kích thước</span>
                  <span className="font-medium text-mocha">
                    {SIZE_LABELS[cakeDesign.size]}
                  </span>
                </div>
                {cakeDesign.flavor && (
                  <div className="flex justify-between items-center">
                    <span className="text-mocha/70 text-sm">Hương vị</span>
                    <span className="font-medium text-mocha">{cakeDesign.flavor}</span>
                  </div>
                )}
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70 text-sm">Loại kem</span>
                  <span className="font-medium text-mocha">
                    {cakeDesign.cream_type || "Kem bơ"}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-mocha/70 text-sm">Màu kem</span>
                  <div className="flex items-center gap-2">
                    <span
                      className="w-5 h-5 rounded-full border border-mocha/20"
                      style={{ backgroundColor: cakeDesign.cream_color }}
                    />
                    <span className="font-medium text-mocha">{cakeDesign.cream_color}</span>
                  </div>
                </div>
                {cakeDesign.topping_type && (
                  <div className="flex justify-between items-center">
                    <span className="text-mocha/70 text-sm">Topping</span>
                    <span className="font-medium text-mocha">{cakeDesign.topping_type}</span>
                  </div>
                )}
                {cakeDesign.special_notes && (
                  <div className="pt-3 border-t border-mocha/10">
                    <span className="text-mocha/70 text-sm block mb-1">Ghi chú</span>
                    <p className="text-mocha text-sm">{cakeDesign.special_notes}</p>
                  </div>
                )}
                <div className="pt-3 border-t border-mocha/10 flex justify-between items-center">
                  <span className="font-medium text-mocha">Tổng tiền</span>
                  <span className="font-bold text-pink-pastel text-xl">
                    {formatPrice(totalPrice)}
                  </span>
                </div>
              </div>
            </section>
          )}

          {/* Customer Info */}
          <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
            <h2 className="font-heading text-lg font-bold text-mocha mb-4">
              Thông tin khách hàng
            </h2>
            <div className="space-y-4">
              {/* Full Name */}
              <div>
                <label htmlFor="fullName" className="block text-sm font-medium text-mocha mb-1">
                  Họ và tên <span className="text-red-500">*</span>
                </label>
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Nguyễn Văn A"
                  className={`w-full px-4 py-3 rounded-xl border text-mocha bg-cream/50 placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px] ${
                    errors.full_name ? "border-red-400" : "border-mocha/20"
                  }`}
                />
                {errors.full_name && (
                  <p className="mt-1 text-sm text-red-600">{errors.full_name}</p>
                )}
              </div>

              {/* Phone */}
              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-mocha mb-1">
                  Số điện thoại <span className="text-red-500">*</span>
                </label>
                <input
                  id="phone"
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="0901234567"
                  maxLength={10}
                  className={`w-full px-4 py-3 rounded-xl border text-mocha bg-cream/50 placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px] ${
                    errors.phone ? "border-red-400" : "border-mocha/20"
                  }`}
                />
                {errors.phone && (
                  <p className="mt-1 text-sm text-red-600">{errors.phone}</p>
                )}
              </div>

              {/* Email (optional) */}
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-mocha mb-1">
                  Email <span className="text-mocha/50">(không bắt buộc)</span>
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@example.com"
                  className={`w-full px-4 py-3 rounded-xl border text-mocha bg-cream/50 placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px] ${
                    errors.email ? "border-red-400" : "border-mocha/20"
                  }`}
                />
                {errors.email && (
                  <p className="mt-1 text-sm text-red-600">{errors.email}</p>
                )}
              </div>
            </div>
          </section>

          {/* Pickup Date - Only show for custom cake builder orders */}
          {isCakeMode && (
            <section className="bg-white rounded-2xl shadow-sm p-5 md:p-6">
              <h2 className="font-heading text-lg font-bold text-mocha mb-4">
                Ngày nhận bánh
              </h2>
              <p className="text-sm text-mocha/60 mb-3">
                {hasTwoTier
                  ? "Bánh 2 tầng cần ít nhất 48 giờ để chuẩn bị"
                  : "Cần ít nhất 24 giờ để chuẩn bị bánh"}
                . Đặt trước tối đa 30 ngày.
              </p>
              <input
                id="pickupDate"
                type="datetime-local"
                value={pickupDate}
                onChange={(e) => setPickupDate(e.target.value)}
                min={formatDateForInput(minDate)}
                max={formatDateForInput(maxDate)}
                className={`w-full px-4 py-3 rounded-xl border text-mocha bg-cream/50 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 min-h-[44px] ${
                  errors.pickup_date ? "border-red-400" : "border-mocha/20"
                }`}
              />
              {errors.pickup_date && (
                <p className="mt-1 text-sm text-red-600">{errors.pickup_date}</p>
              )}
            </section>
          )}

          {/* Submit */}
          <button
            type="submit"
            id="checkout-submit-btn"
            disabled={submitting}
            className="w-full py-4 bg-pink-pastel text-white rounded-full font-bold text-lg hover:bg-pink-pastel/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] shadow-sm"
          >
            {submitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Đang xử lý...
              </span>
            ) : (
              `Xác nhận đặt hàng • ${formatPrice(totalPrice)}`
            )}
          </button>
        </form>
      </div>
    </main>
  );
}

export default function CheckoutPage() {
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
        <CheckoutContent />
      </ProtectedRoute>
    </Suspense>
  );
}

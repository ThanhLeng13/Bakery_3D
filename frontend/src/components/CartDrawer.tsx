"use client";

/**
 * CartDrawer - Slide-out panel displaying cart items.
 * Opens from the right side on icon click in Header.
 */

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useCart } from "@/contexts/CartContext";

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN").format(price) + "đ";
}

export default function CartDrawer() {
  const router = useRouter();
  const {
    items,
    totalItems,
    totalPrice,
    isOpen,
    closeCart,
    removeItem,
    updateQuantity,
  } = useCart();

  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeCart();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [isOpen, closeCart]);

  // Lock body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleCheckout = () => {
    closeCart();
    router.push("/checkout");
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/40 z-40 backdrop-blur-sm transition-opacity"
        onClick={closeCart}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Giỏ hàng"
        className="fixed right-0 top-0 h-full w-full max-w-md z-50 flex flex-col bg-white shadow-2xl"
        style={{ animation: "slideInRight 0.28s cubic-bezier(0.32,0.72,0,1)" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <h2 className="font-heading text-xl font-bold text-mocha">Giỏ bánh ngọt</h2>
            {totalItems > 0 && (
              <span className="bg-pink-pastel text-white text-xs font-bold px-2 py-0.5 rounded-full">
                {totalItems}
              </span>
            )}
          </div>
          <button
            onClick={closeCart}
            className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors text-mocha"
            aria-label="Đóng giỏ hàng"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Cart Items */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-16">
              <div className="w-20 h-20 rounded-full bg-cream flex items-center justify-center mb-4">
                <svg className="w-10 h-10 text-mocha/25" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
                </svg>
              </div>
              <p className="text-mocha/70 font-medium mb-1">Giỏ hàng trống</p>
              <p className="text-mocha/50 text-sm mb-6">Hãy thêm sản phẩm yêu thích vào giỏ!</p>
              <button
                onClick={() => { closeCart(); router.push("/products"); }}
                className="px-5 py-2.5 bg-pink-pastel text-white rounded-full font-medium text-sm hover:bg-pink-pastel/90 transition-colors"
              >
                Xem sản phẩm
              </button>
            </div>
          ) : (
            items.map((item) => (
              <div
                key={item.cartKey}
                className="flex gap-3 p-3 bg-cream/50 rounded-2xl"
              >
                {/* Product image */}
                <div className="w-16 h-16 flex-shrink-0 rounded-xl overflow-hidden bg-gray-100 relative">
                  {item.imageUrl ? (
                    <Image
                      src={item.imageUrl}
                      alt={item.productName}
                      fill
                      sizes="64px"
                      className="object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <svg className="w-7 h-7 text-mocha/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-2.21 0-4 1.79-4 4h8c0-2.21-1.79-4-4-4zM5 12h14v2a4 4 0 01-4 4H9a4 4 0 01-4-4v-2z" />
                      </svg>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-mocha text-sm truncate">{item.productName}</p>
                  {item.expiresAt && (
                    <p className="text-xs text-amber-600 mt-0.5">
                      HSD: {item.expiresAt.split("T")[0].split("-").reverse().join("/")}
                    </p>
                  )}
                  <p className="text-pink-pastel font-semibold text-sm mt-1">
                    {formatPrice(item.unitPrice)}
                  </p>
                </div>

                {/* Quantity + remove */}
                <div className="flex flex-col items-end gap-2">
                  <button
                    onClick={() => removeItem(item.cartKey)}
                    className="w-6 h-6 flex items-center justify-center text-mocha/40 hover:text-red-400 transition-colors"
                    aria-label="Xóa sản phẩm"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>

                  {/* Quantity control */}
                  <div className="flex items-center gap-1 bg-white rounded-full border border-mocha/15 px-1">
                    <button
                      onClick={() => updateQuantity(item.cartKey, item.quantity - 1)}
                      className="w-7 h-7 flex items-center justify-center text-mocha hover:text-pink-pastel transition-colors"
                      aria-label="Giảm số lượng"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                        <path d="M5 12h14" />
                      </svg>
                    </button>
                    <span className="w-6 text-center text-sm font-semibold text-mocha">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.cartKey, item.quantity + 1)}
                      className="w-7 h-7 flex items-center justify-center text-mocha hover:text-pink-pastel transition-colors"
                      aria-label="Tăng số lượng"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                        <path d="M12 5v14M5 12h14" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer — only shown if cart has items */}
        {items.length > 0 && (
          <div className="px-5 py-4 border-t border-gray-100 bg-white">
            {/* Total */}
            <div className="flex justify-between items-center mb-4">
              <span className="text-mocha/70 font-medium">Tổng cộng</span>
              <span className="font-bold text-xl text-mocha">{formatPrice(totalPrice)}</span>
            </div>

            {/* Checkout button */}
            <button
              id="cart-checkout-btn"
              onClick={handleCheckout}
              className="w-full py-3.5 bg-pink-pastel text-white font-bold rounded-full hover:bg-pink-pastel/90 transition-all shadow-md hover:shadow-lg active:scale-[0.98] text-base"
            >
              Mua ngay • {formatPrice(totalPrice)}
            </button>
          </div>
        )}
      </div>

      {/* Slide-in animation */}
      <style>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
      `}</style>
    </>
  );
}

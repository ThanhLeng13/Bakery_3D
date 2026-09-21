"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAuthContext } from "@/contexts/AuthContext";
import { useCart } from "@/contexts/CartContext";
import CartDrawer from "@/components/CartDrawer";
import BrandLogo from "@/components/BrandLogo";
import { useLoyaltyContext } from "@/contexts/LoyaltyContext";

export default function Header() {
  const { user, isAuthenticated, logout } = useAuthContext();
  const { totalItems, openCart } = useCart();
  const { data: loyaltyData } = useLoyaltyContext();
  const router = useRouter();
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  // Hide header on auth pages
  if (pathname?.startsWith("/auth")) return null;

  async function handleLogout() {
    try {
      await logout();
    } catch (e) {
      console.error("Logout failed:", e);
    }
    setUserMenuOpen(false);
    setMenuOpen(false);
    router.push("/");
  }

  const navLinks = [
    { href: "/products", label: "Menu" },
    { href: "/tim-banh", label: "Tìm bằng ảnh" },
    { href: "/cake-builder", label: "Thiết kế bánh" },
    { href: "/orders", label: "Đơn hàng" },
    { href: "/loyalty", label: "Tích điểm" },
  ];

  return (
    <>
    <header className="bg-white border-b border-line sticky top-0 z-50">
      <div className="page-container">
        <div className="flex items-center justify-between gap-4 h-20 sm:h-24">
          {/* Logo */}
          <Link
            href="/"
            className="flex shrink-0 items-center min-h-[44px]"
            aria-label="Bơ Nơ Bakery — Trang chủ"
          >
            <BrandLogo priority />
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors min-h-[40px] flex items-center ${
                  pathname === link.href
                    ? "bg-subtle text-ink"
                    : "text-muted hover:text-ink hover:bg-ink/5"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Cart icon + Auth Area */}
          <div className="flex items-center gap-2">
            {/* Cart button */}
            <button
              id="header-cart-btn"
              onClick={openCart}
              className="relative p-2 rounded-full text-muted hover:text-ink hover:bg-ink/5 transition-colors min-h-[40px] min-w-[40px] flex items-center justify-center"
              aria-label={`Giỏ hàng${totalItems > 0 ? ` (${totalItems} sản phẩm)` : ""}`}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <path d="M16 10a4 4 0 01-8 0" />
              </svg>
              {totalItems > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-action text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none">
                  {totalItems > 99 ? "99+" : totalItems}
                </span>
              )}
            </button>
            {isAuthenticated && user ? (
              /* User Menu */
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen((v) => !v)}
                  className="flex items-center gap-2 px-3 py-2 rounded-full bg-subtle hover:bg-subtle transition-colors min-h-[40px]"
                  aria-expanded={userMenuOpen}
                  aria-haspopup="true"
                >
                  {/* Avatar */}
                  <div className="w-7 h-7 rounded-full bg-action flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                    {user.full_name?.charAt(0)?.toUpperCase() || "U"}
                  </div>
                  <span className="text-sm font-medium text-ink hidden sm:block max-w-[120px] truncate">
                    {user.full_name}
                  </span>
                  {/* Points badge — neutral ink pill, matching the logo palette.
                      Previously an inline avocado-green gradient (#3d6b35 →
                      #8cbd6e) that the Tailwind aliases could not catch because
                      inline styles bypass the theme. */}
                  {loyaltyData && loyaltyData.points > 0 && (
                    <span
                      className="hidden sm:flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-ink text-white"
                      style={{ minHeight: "unset" }}
                    >
                      🎂 {loyaltyData.points.toLocaleString("vi-VN")}
                    </span>
                  )}
                  <svg
                    className={`w-4 h-4 text-muted transition-transform ${userMenuOpen ? "rotate-180" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown */}
                {userMenuOpen && (
                  <>
                    {/* Overlay to close */}
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setUserMenuOpen(false)}
                    />
                    <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl shadow-lg border border-line py-2 z-20 animate-in fade-in slide-in-from-top-2 duration-150">
                      {/* User info */}
                      <div className="px-4 py-3 border-b border-line">
                        <p className="text-sm font-semibold text-ink truncate">{user.full_name}</p>
                        {user.role === "admin" && (
                          <span className="inline-block mt-1 px-2 py-0.5 bg-subtle text-ink text-xs rounded-full font-medium">
                            Admin
                          </span>
                        )}
                        {user.role === "baker" && (
                          <span className="inline-block mt-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs rounded-full font-medium">
                            Thợ bánh
                          </span>
                        )}
                      </div>
                      <div className="py-1">
                        <Link
                          href="/orders"
                          className="flex items-center gap-2 px-4 py-2 text-sm text-ink hover:bg-surface transition-colors"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          📦 Đơn hàng của tôi
                        </Link>
                        <Link
                          href="/loyalty"
                          className="flex items-center gap-2 px-4 py-2 text-sm text-ink hover:bg-surface transition-colors"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <span>🎂 Điểm tích lũy</span>
                          {loyaltyData && loyaltyData.points > 0 && (
                            <span
                              className="ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-ink text-white"
                              style={{ minHeight: "unset" }}
                            >
                              {loyaltyData.points.toLocaleString("vi-VN")}
                            </span>
                          )}
                        </Link>
                        {user.role === "admin" && (
                          <Link
                            href="/admin"
                            className="flex items-center gap-2 px-4 py-2 text-sm text-ink hover:bg-surface transition-colors"
                            onClick={() => setUserMenuOpen(false)}
                          >
                            ⚙️ Quản trị
                          </Link>
                        )}
                        {user.role === "baker" && (
                          <>
                            <Link
                              href="/baker"
                              className="flex items-center gap-2 px-4 py-2 text-sm text-ink hover:bg-surface transition-colors"
                              onClick={() => setUserMenuOpen(false)}
                            >
                              👨‍🍳 Xưởng bánh (Đơn hàng)
                            </Link>
                            <Link
                              href="/baker/inventory"
                              className="flex items-center gap-2 px-4 py-2 text-sm text-ink hover:bg-surface transition-colors"
                              onClick={() => setUserMenuOpen(false)}
                            >
                              📦 Quản lý kho bánh
                            </Link>
                          </>
                        )}
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-500 hover:bg-red-50 transition-colors text-left"
                        >
                          🚪 Đăng xuất
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              /* Login / Register */
              <div className="flex items-center gap-2">
                <Link
                  href="/auth/login"
                  className="hidden lg:flex px-4 py-2 text-sm text-muted hover:text-ink transition-colors min-h-[40px] items-center"
                >
                  Đăng nhập
                </Link>
                {/* Nút CTA chính, theo thiết kế: nền đậm, chữ in hoa giãn nhẹ.
                    Thiết kế Stitch ở header CHỈ có "Đăng nhập" + "Thiết kế ngay",
                    không có nút Đăng ký. Khách tạo tài khoản qua liên kết ở
                    trang đăng nhập, nên header không cần nút đó. */}
                <Link
                  href="/cake-builder"
                  className="hidden sm:flex px-5 py-2.5 bg-action text-surface text-xs font-medium tracking-[0.08em] uppercase rounded-full hover:bg-cocoa transition-colors min-h-[44px] items-center"
                >
                  Thiết kế ngay
                </Link>
              </div>
            )}

            {/* Mobile hamburger */}
            <button
              className="lg:hidden p-2 rounded-lg text-muted hover:text-ink hover:bg-ink/5 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Mở menu"
              aria-expanded={menuOpen}
            >
              {menuOpen ? (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {menuOpen && (
          <div className="lg:hidden py-4 border-t border-line">
            <nav className="flex flex-col gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                    pathname === link.href
                      ? "bg-subtle text-ink"
                      : "text-muted hover:text-ink hover:bg-ink/5"
                  }`}
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              {!isAuthenticated && (
                <>
                  <Link
                    href="/auth/login"
                    className="px-4 py-3 rounded-xl text-sm font-medium text-muted hover:text-ink hover:bg-ink/5 transition-colors"
                    onClick={() => setMenuOpen(false)}
                  >
                    Đăng nhập
                  </Link>
                  {/* Nút Đăng ký chỉ có ở menu mobile: phần header ẩn nút Đăng
                      nhập dưới breakpoint lg, nên nếu không có ở đây thì khách
                      trên điện thoại không có đường vào tài khoản. Desktop giữ
                      đúng thiết kế (chỉ Đăng nhập). */}
                  <Link
                    href="/auth/register"
                    className="px-4 py-3 rounded-xl text-sm font-medium text-muted hover:text-ink hover:bg-ink/5 transition-colors"
                    onClick={() => setMenuOpen(false)}
                  >
                    Đăng ký
                  </Link>
                </>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>

    {/* Cart Drawer — rendered outside header so it overlays whole page */}
    <CartDrawer />
    </>
  );
}

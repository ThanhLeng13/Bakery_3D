"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { useAuthContext } from "@/contexts/AuthContext";
import { useCart } from "@/contexts/CartContext";
import CartDrawer from "@/components/CartDrawer";
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
    { href: "/cake-builder", label: "Thiết kế bánh" },
    { href: "/orders", label: "Đơn hàng" },
    { href: "/loyalty", label: "🌿 Tích điểm" },
  ];

  return (
    <>
    <header className="bg-white/90 backdrop-blur-md border-b border-mocha/10 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link
            href="/"
            className="font-heading text-xl text-mocha font-bold flex items-center gap-2 hover:text-pink-pastel transition-colors min-h-[44px]"
          >
            🎂 <span>Bơ Nơ</span>
          </Link>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors min-h-[40px] flex items-center ${
                  pathname === link.href
                    ? "bg-pink-pastel/10 text-pink-pastel"
                    : "text-mocha/70 hover:text-mocha hover:bg-mocha/5"
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
              className="relative p-2 rounded-full text-mocha/70 hover:text-mocha hover:bg-mocha/5 transition-colors min-h-[40px] min-w-[40px] flex items-center justify-center"
              aria-label={`Giỏ hàng${totalItems > 0 ? ` (${totalItems} sản phẩm)` : ""}`}
            >
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <path d="M16 10a4 4 0 01-8 0" />
              </svg>
              {totalItems > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-pink-pastel text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none">
                  {totalItems > 99 ? "99+" : totalItems}
                </span>
              )}
            </button>
            {isAuthenticated && user ? (
              /* User Menu */
              <div className="relative">
                <button
                  onClick={() => setUserMenuOpen((v) => !v)}
                  className="flex items-center gap-2 px-3 py-2 rounded-full bg-pink-pastel/10 hover:bg-pink-pastel/20 transition-colors min-h-[40px]"
                  aria-expanded={userMenuOpen}
                  aria-haspopup="true"
                >
                  {/* Avatar */}
                  <div className="w-7 h-7 rounded-full bg-pink-pastel flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                    {user.full_name?.charAt(0)?.toUpperCase() || "U"}
                  </div>
                  <span className="text-sm font-medium text-mocha hidden sm:block max-w-[120px] truncate">
                    {user.full_name}
                  </span>
                  {/* Points badge */}
                  {loyaltyData && loyaltyData.points > 0 && (
                    <span
                      className="hidden sm:flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[10px] font-bold"
                      style={{
                        background: "linear-gradient(135deg, #3d6b35 0%, #8cbd6e 100%)",
                        color: "white",
                        boxShadow: "0 2px 6px rgba(61,107,53,0.3)",
                        minHeight: "unset",
                      }}
                    >
                      🌿 {loyaltyData.points.toLocaleString("vi-VN")}
                    </span>
                  )}
                  <svg
                    className={`w-4 h-4 text-mocha/50 transition-transform ${userMenuOpen ? "rotate-180" : ""}`}
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
                    <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl shadow-lg border border-mocha/10 py-2 z-20 animate-in fade-in slide-in-from-top-2 duration-150">
                      {/* User info */}
                      <div className="px-4 py-3 border-b border-mocha/10">
                        <p className="text-sm font-semibold text-mocha truncate">{user.full_name}</p>
                        {user.role === "admin" && (
                          <span className="inline-block mt-1 px-2 py-0.5 bg-pink-pastel/10 text-pink-pastel text-xs rounded-full font-medium">
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
                          className="flex items-center gap-2 px-4 py-2 text-sm text-mocha hover:bg-cream transition-colors"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          📦 Đơn hàng của tôi
                        </Link>
                        <Link
                          href="/loyalty"
                          className="flex items-center gap-2 px-4 py-2 text-sm text-mocha hover:bg-cream transition-colors"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          <span>🌿 Điểm tích lũy</span>
                          {loyaltyData && loyaltyData.points > 0 && (
                            <span
                              className="ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-bold"
                              style={{
                                background: "linear-gradient(135deg, #3d6b35, #8cbd6e)",
                                color: "white",
                                minHeight: "unset",
                              }}
                            >
                              {loyaltyData.points.toLocaleString("vi-VN")}
                            </span>
                          )}
                        </Link>
                        {user.role === "admin" && (
                          <Link
                            href="/admin"
                            className="flex items-center gap-2 px-4 py-2 text-sm text-mocha hover:bg-cream transition-colors"
                            onClick={() => setUserMenuOpen(false)}
                          >
                            ⚙️ Quản trị
                          </Link>
                        )}
                        {user.role === "baker" && (
                          <>
                            <Link
                              href="/baker"
                              className="flex items-center gap-2 px-4 py-2 text-sm text-mocha hover:bg-cream transition-colors"
                              onClick={() => setUserMenuOpen(false)}
                            >
                              👨‍🍳 Xưởng bánh (Đơn hàng)
                            </Link>
                            <Link
                              href="/baker/inventory"
                              className="flex items-center gap-2 px-4 py-2 text-sm text-mocha hover:bg-cream transition-colors"
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
                  className="hidden sm:flex px-4 py-2 text-sm font-medium text-mocha/70 hover:text-mocha transition-colors min-h-[40px] items-center"
                >
                  Đăng nhập
                </Link>
                <Link
                  href="/auth/register"
                  className="px-4 py-2 bg-pink-pastel text-white text-sm font-medium rounded-full hover:bg-pink-pastel/90 transition-colors min-h-[40px] flex items-center"
                >
                  Đăng ký
                </Link>
              </div>
            )}

            {/* Mobile hamburger */}
            <button
              className="md:hidden p-2 rounded-lg text-mocha/70 hover:text-mocha hover:bg-mocha/5 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
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
          <div className="md:hidden py-3 border-t border-mocha/10">
            <nav className="flex flex-col gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                    pathname === link.href
                      ? "bg-pink-pastel/10 text-pink-pastel"
                      : "text-mocha/70 hover:text-mocha hover:bg-mocha/5"
                  }`}
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                </Link>
              ))}
              {!isAuthenticated && (
                <Link
                  href="/auth/login"
                  className="px-4 py-3 rounded-xl text-sm font-medium text-mocha/70 hover:text-mocha hover:bg-mocha/5 transition-colors"
                  onClick={() => setMenuOpen(false)}
                >
                  Đăng nhập
                </Link>
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

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getStoredUser, isAuthenticated, logout, AuthUser } from "@/lib/auth";

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuth, setIsAuth] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (isAuthenticated()) {
      setIsAuth(true);
      setUser(getStoredUser());
    }
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
    } catch (e) {
      console.error("Logout failed:", e);
    }
    setIsAuth(false);
    setUser(null);
    setIsMobileMenuOpen(false);
    router.push("/");
    router.refresh();
  };

  return (
    <nav className="bg-white/85 backdrop-blur-md border-b border-mocha/10 sticky top-0 z-50 shadow-sm transition-all duration-300">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-heading text-xl text-mocha font-bold flex items-center gap-1 hover:text-pink-pastel transition-colors min-h-[44px]">
          🎂 La Douceur
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/products"
            className="px-4 py-2 text-sm font-body text-mocha/70 hover:text-mocha hover:bg-pink-pastel/5 rounded-full transition-colors min-h-[44px] flex items-center"
          >
            Menu
          </Link>
          <Link
            href="/cake-builder"
            className="px-4 py-2 text-sm font-body text-mocha/70 hover:text-mocha hover:bg-pink-pastel/5 rounded-full transition-colors min-h-[44px] flex items-center"
          >
            Thiết kế bánh
          </Link>
          <Link
            href="/orders"
            className="px-4 py-2 text-sm font-body text-mocha/70 hover:text-mocha hover:bg-pink-pastel/5 rounded-full transition-colors min-h-[44px] flex items-center"
          >
            Đơn hàng
          </Link>
          {isAuth && user ? (
            <div className="flex items-center gap-3 pl-2 border-l border-mocha/10">
              <span className="text-sm font-body text-mocha font-medium max-w-[120px] truncate" title={user.full_name}>
                👤 {user.full_name}
              </span>
              <button
                onClick={handleLogout}
                className="px-4 py-2 bg-mocha/5 text-mocha hover:bg-mocha/10 text-sm font-body font-medium rounded-full transition-colors min-h-[44px] flex items-center"
              >
                Đăng xuất
              </button>
            </div>
          ) : (
            <Link
              href="/auth/login"
              className="px-4 py-2 bg-pink-pastel text-white text-sm font-body font-medium rounded-full hover:bg-pink-pastel/90 hover:shadow-sm transition-all min-h-[44px] flex items-center"
            >
              Đăng nhập
            </Link>
          )}
        </div>

        {/* Mobile Menu Button */}
        <div className="flex md:hidden items-center">
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="p-2 text-mocha hover:text-pink-pastel transition-colors focus:outline-none min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-expanded={isMobileMenuOpen}
            aria-label={isMobileMenuOpen ? "Đóng menu" : "Mở menu"}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              {isMobileMenuOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Drawer/Dropdown */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-mocha/10 bg-white/95 backdrop-blur-md transition-all duration-300">
          <div className="px-4 pt-2 pb-4 space-y-2">
            <Link
              href="/products"
              onClick={() => setIsMobileMenuOpen(false)}
              className="block px-4 py-3 text-base font-body text-mocha/70 hover:text-mocha hover:bg-pink-pastel/5 rounded-lg transition-colors"
            >
              Menu
            </Link>
            <Link
              href="/cake-builder"
              onClick={() => setIsMobileMenuOpen(false)}
              className="block px-4 py-3 text-base font-body text-mocha/70 hover:text-mocha hover:bg-pink-pastel/5 rounded-lg transition-colors"
            >
              Thiết kế bánh
            </Link>
            <Link
              href="/orders"
              onClick={() => setIsMobileMenuOpen(false)}
              className="block px-4 py-3 text-base font-body text-mocha/70 hover:text-mocha hover:bg-pink-pastel/5 rounded-lg transition-colors"
            >
              Đơn hàng
            </Link>
            {isAuth && user ? (
              <div className="pt-2 border-t border-mocha/10 space-y-2">
                <div className="px-4 py-2 text-sm font-body text-mocha font-medium flex items-center gap-2">
                  👤 <span className="truncate">{user.full_name}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="w-full text-left px-4 py-3 bg-mocha/5 text-mocha hover:bg-mocha/10 text-base font-body font-medium rounded-lg transition-colors"
                >
                  Đăng xuất
                </button>
              </div>
            ) : (
              <Link
                href="/auth/login"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block text-center px-4 py-3 bg-pink-pastel text-white text-base font-body font-medium rounded-full hover:bg-pink-pastel/90 transition-all"
              >
                Đăng nhập
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
}

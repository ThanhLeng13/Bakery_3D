"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getStoredUser, isAuthenticated, logout, AuthUser } from "@/lib/auth";

export default function Header() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuth, setIsAuth] = useState(false);

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
    router.push("/");
    router.refresh();
  };

  return (
    <nav className="bg-white/85 backdrop-blur-md border-b border-mocha/10 sticky top-0 z-30 shadow-sm transition-all duration-300">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-heading text-xl text-mocha font-bold flex items-center gap-1 hover:text-pink-pastel transition-colors">
          🎂 La Douceur
        </Link>
        <div className="flex items-center gap-3">
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
      </div>
    </nav>
  );
}

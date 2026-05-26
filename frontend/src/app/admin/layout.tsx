"use client";

/**
 * Admin layout with sidebar navigation.
 * Protected by ProtectedRoute with allowedRoles=["admin"].
 */

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthContext } from "@/contexts/AuthContext";

const navItems = [
  { href: "/admin/products", label: "Sản phẩm", icon: "🧁" },
  { href: "/admin/orders", label: "Đơn hàng", icon: "📦" },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
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
      <ProtectedRoute allowedRoles={["admin"]}>
        <AdminShell>{children}</AdminShell>
      </ProtectedRoute>
    </Suspense>
  );
}

function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthContext();

  return (
    <div className="min-h-screen bg-cream flex">
      {/* Sidebar */}
      <aside className="hidden md:flex md:w-64 flex-col bg-white border-r border-mocha/10 shadow-sm">
        <div className="p-6 border-b border-mocha/10">
          <h1 className="font-heading text-xl text-mocha font-bold">
            Admin Panel
          </h1>
          <p className="text-sm text-mocha/60 font-body mt-1">
            {user?.full_name || "Admin"}
          </p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg font-body text-sm transition-colors ${
                  isActive
                    ? "bg-pink-pastel/10 text-pink-pastel font-medium"
                    : "text-mocha/70 hover:bg-cream hover:text-mocha"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-mocha/10">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg font-body text-sm text-mocha/70 hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <span className="text-lg">🚪</span>
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="flex-1 flex flex-col">
        <header className="md:hidden flex items-center justify-between p-4 bg-white border-b border-mocha/10 shadow-sm">
          <h1 className="font-heading text-lg text-mocha font-bold">
            Admin Panel
          </h1>
          <MobileNav pathname={pathname} onLogout={logout} />
        </header>

        {/* Main content */}
        <main className="flex-1 p-4 md:p-8 overflow-auto">{children}</main>
      </div>
    </div>
  );
}

function MobileNav({
  pathname,
  onLogout,
}: {
  pathname: string;
  onLogout: () => void;
}) {
  return (
    <nav className="flex items-center gap-2">
      {navItems.map((item) => {
        const isActive = pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`px-3 py-2 rounded-lg text-sm font-body transition-colors ${
              isActive
                ? "bg-pink-pastel/10 text-pink-pastel font-medium"
                : "text-mocha/70"
            }`}
          >
            {item.icon}
          </Link>
        );
      })}
      <button
        onClick={onLogout}
        className="px-3 py-2 rounded-lg text-sm text-mocha/70 hover:text-red-600"
      >
        🚪
      </button>
    </nav>
  );
}

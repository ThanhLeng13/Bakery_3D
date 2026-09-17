"use client";

/**
 * Manager layout with sidebar navigation.
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
  { href: "/admin/inventory", label: "Kho bánh", icon: "🏷️" },
  { href: "/admin/options", label: "Thuộc tính bánh", icon: "🎨" },
  { href: "/admin/users", label: "Nhân sự", icon: "👥" },
];

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-surface">
          <div className="animate-pulse flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-subtle" />
            <p className="text-muted font-body">Đang tải...</p>
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
    <div className="min-h-screen bg-surface flex">
      {/* Sidebar */}
      <aside className="hidden md:flex md:w-64 flex-col bg-white border-r border-line shadow-sm">
        <div className="p-6 border-b border-line">
          <Link href="/admin/products" className="hover:text-ink transition-colors">
            <h1 className="font-heading text-xl text-ink font-bold">
              Khu quản lý
            </h1>
          </Link>
          <p className="text-sm text-muted font-body mt-1">
            {user?.full_name || "Quản lý"}
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
                    ? "bg-subtle text-ink font-medium"
                    : "text-muted hover:bg-surface hover:text-ink"
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-line space-y-1">
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-4 py-3 rounded-lg font-body text-sm text-muted hover:bg-red-50 hover:text-red-600 transition-colors"
          >
            <span className="text-lg">🚪</span>
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Mobile header */}
      <div className="flex-1 flex flex-col">
        <header className="md:hidden flex items-center justify-between p-4 bg-white border-b border-line shadow-sm">
          <Link href="/admin/products" className="hover:text-ink transition-colors">
            <h1 className="font-heading text-lg text-ink font-bold">
              Khu quản lý
            </h1>
          </Link>
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
                ? "bg-subtle text-ink font-medium"
                : "text-muted"
            }`}
          >
            {item.icon}
          </Link>
        );
      })}
      <button
        onClick={onLogout}
        className="px-3 py-2 rounded-lg text-sm text-muted hover:text-red-600"
      >
        🚪
      </button>
    </nav>
  );
}

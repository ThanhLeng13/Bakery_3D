"use client";

/**
 * Baker layout.
 *
 * /baker has no shell of its own, so before this file the only pages reachable
 * with a baker role (Bảng điều khiển thợ bánh, Quản lý kho bánh) rendered no
 * navigation and — because they do not mount the site <Header /> — offered no
 * way to sign out. This shell provides the nav between the two baker screens
 * plus the logout button, mirroring the staff and admin layouts.
 *
 * allowedRoles includes "admin" because the bakery inventory screen is also
 * reachable by a manager (see app/baker/inventory/page.tsx); RoleBoundary
 * already keeps managers inside /admin, so this stays a second safety net.
 */

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthContext } from "@/contexts/AuthContext";

const navItems = [
  { href: "/baker/orders", label: "Đơn hàng", icon: "📋" },
  { href: "/baker/inventory", label: "Kho bánh", icon: "🏷️" },
];

export default function BakerLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-surface" />}>
      <ProtectedRoute allowedRoles={["baker", "admin"]}>
        <BakerShell>{children}</BakerShell>
      </ProtectedRoute>
    </Suspense>
  );
}

function BakerShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuthContext();

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-40 border-b border-line bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <Link href="/baker/orders" className="shrink-0 hover:opacity-80 transition-opacity">
            <h1 className="font-heading text-xl font-bold text-ink">Xưởng bánh</h1>
            <p className="text-xs text-muted">
              Thợ bánh: {user?.full_name || "Bán hàng"}
            </p>
          </Link>

          <div className="flex items-center gap-2">
            <nav className="flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    // The label span is display:none below the sm breakpoint and
                    // the icon is aria-hidden, so without this the link has no
                    // accessible name on small screens.
                    aria-label={item.label}
                    className={`flex items-center gap-2 rounded-full px-3 py-2 text-sm transition-colors ${
                      isActive
                        ? "bg-subtle font-medium text-ink"
                        : "text-muted hover:bg-surface hover:text-ink"
                    }`}
                  >
                    <span aria-hidden="true">{item.icon}</span>
                    <span className="hidden sm:inline">{item.label}</span>
                  </Link>
                );
              })}
            </nav>
            <button
              onClick={logout}
              className="min-h-[40px] rounded-full px-4 py-2 text-sm font-medium text-red-500 transition-colors hover:bg-red-50 hover:text-red-600"
            >
              Đăng xuất
            </button>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}

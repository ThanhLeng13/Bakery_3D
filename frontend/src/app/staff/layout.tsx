"use client";

import { Suspense } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthContext } from "@/contexts/AuthContext";

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="min-h-screen bg-surface" />}>
      <ProtectedRoute allowedRoles={["staff"]}>
        <StaffShell>{children}</StaffShell>
      </ProtectedRoute>
    </Suspense>
  );
}

function StaffShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuthContext();

  return (
    <div className="min-h-screen bg-surface">
      <header className="sticky top-0 z-40 border-b border-line bg-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
          <div>
            <h1 className="font-heading text-xl font-bold text-ink">Quầy bán hàng</h1>
            <p className="text-xs text-muted">
              Nhân viên: {user?.full_name || "Bán hàng"}
            </p>
          </div>
          <button
            onClick={logout}
            className="min-h-[40px] rounded-full px-4 text-sm font-medium text-red-500 hover:bg-red-50 hover:text-red-600"
          >
            Đăng xuất
          </button>
        </div>
      </header>
      {children}
    </div>
  );
}

"use client";

/**
 * Protected route wrapper component.
 * Redirects to login page if user is not authenticated.
 * Preserves the current URL as redirect parameter.
 */

import { useEffect } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { useAuthContext } from "@/contexts/AuthContext";
import { UserRole } from "@/types";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Optional: restrict access to specific roles */
  allowedRoles?: UserRole[];
}

export default function ProtectedRoute({
  children,
  allowedRoles,
}: ProtectedRouteProps) {
  const { user, loading, isAuthenticated } = useAuthContext();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    // Chờ async validate xong mới xử lý
    if (loading) return;

    if (!isAuthenticated) {
      const currentUrl = pathname + (searchParams.toString() ? `?${searchParams.toString()}` : "");
      router.replace(`/auth/login?redirect=${encodeURIComponent(currentUrl)}`);
      return;
    }

    // Kiểm tra role
    if (allowedRoles && user && !allowedRoles.includes(user.role)) {
      router.replace("/");
    }
  }, [loading, isAuthenticated, user, allowedRoles, router, pathname, searchParams]);

  // Hiện spinner trong khi đang xác thực token (kể cả khi có stored user)
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cream">
        <div className="animate-pulse flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-pink-pastel/30" />
          <p className="text-mocha/60 font-body">Đang kiểm tra phiên đăng nhập...</p>
        </div>
      </div>
    );
  }

  // Sau khi loading xong: không có auth → null (useEffect đã redirect)
  if (!isAuthenticated) {
    return null;
  }

  // Không đủ quyền
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return null;
  }

  return <>{children}</>;
}

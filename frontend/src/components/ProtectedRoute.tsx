
"use client";

/**
 * Protected route wrapper component.
 * Redirects to login page if user is not authenticated.
 * Preserves the current URL as redirect parameter.
 *
 * allowedRolesKey (a serialised string) is used in the useEffect dependency
 * array instead of the allowedRoles array prop, because callers often pass
 * inline literals (e.g. allowedRoles={["baker"]}) which create a new array
 * reference on every render and would cause an infinite redirect loop.
 * The role-check inside the effect derives the set from allowedRolesKey so
 * the exhaustive-deps rule is satisfied without introducing instability.
 */

import { useEffect, useMemo } from "react";
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

  // Serialize allowedRoles to a stable string so that inline array literals
  // (new reference each render) do not trigger the effect unnecessarily.
  const allowedRolesKey = useMemo(
    () => allowedRoles?.join(",") ?? "",
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [allowedRoles?.join(",")]
  );

  useEffect(() => {
    // Chờ async validate xong mới xử lý
    if (loading) return;

    if (!isAuthenticated) {
      const currentUrl = pathname + (searchParams.toString() ? `?${searchParams.toString()}` : "");
      router.replace(`/auth/login?redirect=${encodeURIComponent(currentUrl)}`);
      return;
    }

    // Derive the allowed set from the stable string key — avoids referencing
    // the allowedRoles array prop directly, which would require it in deps and
    // cause infinite loops when callers pass inline array literals.
    if (allowedRolesKey) {
      const roles = allowedRolesKey.split(",") as UserRole[];
      if (!user || !roles.includes(user.role)) {
        router.replace("/");
      }
    }
  }, [loading, isAuthenticated, user, allowedRolesKey, router, pathname, searchParams]);

  // Hiện spinner trong khi đang xác thực token
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

  // Kiểm tra role tại render: nếu allowedRoles được chỉ định,
  // user phải tồn tại và có role hợp lệ — user=null không được pass
  if (allowedRoles) {
    if (!user || !allowedRoles.includes(user.role)) {
      return null;
    }
  }

  return <>{children}</>;
}

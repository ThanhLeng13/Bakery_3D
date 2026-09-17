"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuthContext } from "@/contexts/AuthContext";
import { getRoleHome, isPathAllowedForRole } from "@/lib/roles";

export default function RoleBoundary({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuthContext();
  const pathname = usePathname();
  const router = useRouter();
  const allowed = !user || isPathAllowedForRole(user.role, pathname);

  useEffect(() => {
    if (!loading && user && !allowed) {
      router.replace(getRoleHome(user.role));
    }
  }, [allowed, loading, router, user]);

  if (!loading && user && !allowed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <p className="text-muted">Đang chuyển đến khu vực làm việc...</p>
      </div>
    );
  }

  return <>{children}</>;
}

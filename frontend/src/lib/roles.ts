import type { UserRole } from "@/types";

const INTERNAL_PREFIXES = ["/staff", "/admin", "/baker"];

export function getRoleHome(role: UserRole): string {
  switch (role) {
    case "staff":
      return "/staff/sales";
    case "admin":
      return "/admin/products";
    case "baker":
      return "/baker/orders";
    default:
      return "/";
  }
}

export function isPathAllowedForRole(role: UserRole, pathname: string): boolean {
  if (pathname.startsWith("/auth")) return true;

  if (role === "customer") {
    return !INTERNAL_PREFIXES.some((prefix) => pathname.startsWith(prefix));
  }

  const home = getRoleHome(role);
  const prefix = home.split("/").slice(0, 2).join("/");
  return pathname.startsWith(prefix);
}

export function resolveLoginDestination(
  role: UserRole,
  requestedPath: string | null,
): string {
  if (requestedPath && requestedPath.startsWith("/") && isPathAllowedForRole(role, requestedPath)) {
    return requestedPath;
  }
  return getRoleHome(role);
}

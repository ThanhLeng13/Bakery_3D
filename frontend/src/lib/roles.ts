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
  // A protocol-relative URL ("//evil.example") also starts with "/", so a bare
  // startsWith("/") check would accept it and send the user off-site after
  // login. Require a single leading slash and reject the "//" form.
  const isInternalPath =
    !!requestedPath &&
    requestedPath.startsWith("/") &&
    !requestedPath.startsWith("//");

  if (isInternalPath && isPathAllowedForRole(role, requestedPath)) {
    return requestedPath;
  }
  return getRoleHome(role);
}

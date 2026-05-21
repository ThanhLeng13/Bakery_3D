/**
 * Auth utilities: login, register, logout, refreshToken, getStoredToken, isAuthenticated.
 * Manages JWT tokens in localStorage with auto-refresh logic.
 */

import { apiClient } from "./api";
import { UserRole } from "@/types";

// --- Storage Keys ---
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "auth_user";

// --- Types ---
export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role: UserRole;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  phone: string;
}

export interface LoginData {
  email: string;
  password: string;
}

// --- Token Storage ---
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

function storeAuthData(data: AuthResponse): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// --- Token Expiry Check ---
function parseJwtPayload(token: string): { exp?: number } | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function isTokenExpiringSoon(thresholdMinutes: number = 5): boolean {
  const token = getStoredToken();
  if (!token) return true;

  const payload = parseJwtPayload(token);
  if (!payload?.exp) return true;

  const expiresAt = payload.exp * 1000; // convert to ms
  const now = Date.now();
  const thresholdMs = thresholdMinutes * 60 * 1000;

  return expiresAt - now < thresholdMs;
}

export function isAuthenticated(): boolean {
  const token = getStoredToken();
  if (!token) return false;

  const payload = parseJwtPayload(token);
  if (!payload?.exp) return false;

  // Token is still valid (not fully expired)
  return payload.exp * 1000 > Date.now();
}

// --- Auth API Calls ---
export async function login(data: LoginData): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/login", data);
  storeAuthData(response);
  return response;
}

export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>("/api/v1/auth/register", data);
  storeAuthData(response);
  return response;
}

export async function logout(): Promise<void> {
  const token = getStoredToken();
  if (token) {
    try {
      await apiClient.post("/api/v1/auth/logout", { access_token: token });
    } catch {
      // Logout should always clear local state even if API call fails
    }
  }
  clearTokens();
}

export async function refreshToken(): Promise<AuthResponse | null> {
  const refresh = getStoredRefreshToken();
  if (!refresh) return null;

  try {
    const response = await apiClient.post<AuthResponse>("/api/v1/auth/refresh", {
      refresh_token: refresh,
    });
    storeAuthData(response);
    return response;
  } catch {
    clearTokens();
    return null;
  }
}

// --- Auto-Refresh Logic ---
let refreshInterval: ReturnType<typeof setInterval> | null = null;

export function startAutoRefresh(): void {
  stopAutoRefresh();

  // Check every 60 seconds if token needs refresh
  refreshInterval = setInterval(async () => {
    if (isTokenExpiringSoon(5)) {
      await refreshToken();
    }
  }, 60_000);
}

export function stopAutoRefresh(): void {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

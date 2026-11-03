/**
 * API client with base URL, JWT header injection, and 401 interceptor.
 * Handles automatic token refresh and redirect on auth failure.
 */

import { getStoredToken, clearTokens } from "./auth";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiError {
  detail: string | Array<{ field: string; message: string }>;
  retry_after?: number;
  /** Mã HTTP của phản hồi lỗi, để nơi gọi phân biệt 401 với 5xx. */
  status?: number;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    const token = getStoredToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  private getRedirectUrl(): string {
    if (typeof window === "undefined") return "/auth/login";
    const currentPath = window.location.pathname + window.location.search;
    return `/auth/login?redirect=${encodeURIComponent(currentPath)}`;
  }

  private handle401(): never {
    clearTokens();
    if (typeof window !== "undefined") {
      window.location.href = this.getRedirectUrl();
    }
    throw new Error("Unauthorized");
  }

  /**
   * Các endpoint ĐANG xác thực, phải tự xử lý 401 của chính nó.
   *
   * Interceptor 401 toàn cục dùng cho phiên hết hạn: xoá token rồi chuyển về
   * trang đăng nhập. Áp nó cho chính request đăng nhập là sai: mật khẩu sai trả
   * 401, nên `handle401` chạy `window.location.href = "/auth/login"` — tải lại
   * trang đăng nhập và xoá thông báo lỗi vừa đặt. Người dùng bấm "Đăng nhập",
   * thấy trang nhấp nháy rồi quay về form trắng, nên hiểu là "đăng nhập không
   * được" mà không biết vì sao.
   *
   * Nó còn thay lỗi thật bằng `Error("Unauthorized")`, nên nơi gọi mất cả
   * `detail` lẫn `retry_after` và không thể phân biệt sai mật khẩu với lỗi
   * server.
   */
  private static readonly AUTH_PATHS = [
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/oauth/google",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
  ];

  private isAuthPath(path: string): boolean {
    return ApiClient.AUTH_PATHS.some((p) => path.startsWith(p));
  }

  private async handleResponse<T>(response: Response, path: string): Promise<T> {
    if (response.status === 401 && !this.isAuthPath(path)) {
      this.handle401();
    }

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "Đã xảy ra lỗi, vui lòng thử lại sau",
      }));
      // Giữ mã HTTP để nơi gọi phân biệt được 401 (sai thông tin đăng nhập)
      // với 5xx (lỗi server) thay vì in cùng một câu cho mọi trường hợp.
      error.status = response.status;
      throw error;
    }

    // 204 No Content — nothing to parse
    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response, path);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response, path);
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response, path);
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PATCH",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response, path);
  }

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response, path);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

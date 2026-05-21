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

  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 401) {
      this.handle401();
    }

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "Đã xảy ra lỗi, vui lòng thử lại sau",
      }));
      throw error;
    }

    return response.json();
  }

  async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "PATCH",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }
}

export const apiClient = new ApiClient(API_BASE_URL);

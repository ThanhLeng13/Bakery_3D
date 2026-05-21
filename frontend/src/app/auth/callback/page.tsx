"use client";

/**
 * OAuth callback handler page.
 * Receives the access_token from Google OAuth flow,
 * stores tokens, and redirects to the intended page.
 */

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { AuthResponse } from "@/lib/auth";

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-cream">
          <div className="w-12 h-12 rounded-full border-4 border-pink-pastel border-t-transparent animate-spin" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState("");

  useEffect(() => {
    async function handleCallback() {
      const accessToken = searchParams.get("access_token");
      const redirectUrl = searchParams.get("redirect") || "/";

      if (!accessToken) {
        setError("Không nhận được thông tin xác thực từ Google");
        return;
      }

      try {
        // Exchange Google access token for our JWT
        const response = await apiClient.post<AuthResponse>(
          "/api/v1/auth/oauth/google",
          { access_token: accessToken }
        );

        // Store tokens
        localStorage.setItem("access_token", response.access_token);
        localStorage.setItem("refresh_token", response.refresh_token);
        localStorage.setItem("auth_user", JSON.stringify(response.user));

        // Redirect to intended page
        router.replace(redirectUrl);
      } catch {
        setError("Đăng nhập bằng Google thất bại. Vui lòng thử lại.");
      }
    }

    handleCallback();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cream px-4">
        <div className="text-center">
          <div className="mb-4 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 font-body">
            {error}
          </div>
          <a
            href="/auth/login"
            className="text-pink-pastel hover:text-pink-pastel/80 font-medium font-body transition-colors"
          >
            Quay lại trang đăng nhập
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full border-4 border-pink-pastel border-t-transparent animate-spin" />
        <p className="text-mocha/70 font-body">Đang xác thực...</p>
      </div>
    </div>
  );
}

"use client";

/**
 * Reset Password page.
 * Supabase redirects here after user clicks the email link:
 *   /auth/reset-password#access_token=xxx&refresh_token=yyy&type=recovery
 *
 * This page reads the token from the URL hash, then lets the user
 * enter a new password, which is sent to the backend API.
 */

import { Suspense, useState, FormEvent, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiClient, ApiError } from "@/lib/api";

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-cream">
          <div className="animate-pulse flex flex-col items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-pink-pastel/30" />
            <p className="text-mocha/60 font-body">Đang tải...</p>
          </div>
        </div>
      }
    >
      <ResetPasswordContent />
    </Suspense>
  );
}

function ResetPasswordContent() {
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [refreshToken, setRefreshToken] = useState<string | null>(null);
  const [tokenError, setTokenError] = useState(false);

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  // Extract token from URL fragment (Supabase sends #access_token=...&refresh_token=...&type=recovery)
  useEffect(() => {
    const hash = window.location.hash;
    if (!hash) {
      setTokenError(true);
      return;
    }
    const params = new URLSearchParams(hash.slice(1)); // remove leading #
    const token = params.get("access_token");
    const rToken = params.get("refresh_token");
    const type = params.get("type");

    if (!token || type !== "recovery") {
      setTokenError(true);
      return;
    }
    setAccessToken(token);
    setRefreshToken(rToken);
    // Clear hash so the sensitive token is not left exposed in the address bar
    window.location.hash = "";
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Mật khẩu xác nhận không khớp.");
      return;
    }

    if (!accessToken) {
      setError("Token không hợp lệ. Vui lòng yêu cầu link mới.");
      return;
    }

    setLoading(true);
    try {
      await apiClient.post("/api/v1/auth/reset-password", {
        access_token: accessToken,
        refresh_token: refreshToken ?? "",
        new_password: newPassword,
      });
      setSuccess(true);
      // Redirect to login after 3 seconds
      setTimeout(() => router.push("/auth/login"), 3000);
    } catch (err: unknown) {
      const apiError = err as ApiError;
      const detail = apiError?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d) => d.message).join(", "));
      } else {
        setError("Không thể đặt lại mật khẩu. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  }

  // Invalid / missing token
  if (tokenError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cream px-4">
        <div className="w-full max-w-md bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="text-5xl mb-4">⚠️</div>
          <h1 className="text-2xl font-heading text-mocha mb-2">Link không hợp lệ</h1>
          <p className="text-mocha/70 font-body text-sm mb-6">
            Link khôi phục mật khẩu này đã hết hạn hoặc không hợp lệ.
            Vui lòng yêu cầu link mới.
          </p>
          <Link
            href="/auth/forgot-password"
            className="inline-block px-6 py-3 bg-pink-pastel text-white rounded-full font-medium hover:bg-pink-pastel/90 transition-colors"
          >
            Yêu cầu link mới
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream px-4 py-8">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🔐</div>
          <h1 className="text-3xl font-heading text-mocha mb-2">Đặt mật khẩu mới</h1>
          <p className="text-mocha/70 font-body">Nhập mật khẩu mới cho tài khoản của bạn</p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          {success ? (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <h2 className="text-xl font-heading text-mocha mb-2">Đặt lại thành công!</h2>
              <p className="text-mocha/70 font-body text-sm mb-4">
                Mật khẩu của bạn đã được cập nhật. Đang chuyển hướng đến trang đăng nhập...
              </p>
              <div className="flex justify-center">
                <div className="animate-spin w-5 h-5 border-2 border-pink-pastel border-t-transparent rounded-full" />
              </div>
            </div>
          ) : (
            <>
              {error && (
                <div
                  className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-body"
                  role="alert"
                >
                  {error}
                </div>
              )}

              {/* Password requirements hint */}
              <div className="mb-5 p-3 rounded-lg bg-amber-50 border border-amber-100 text-amber-700 text-xs font-body">
                Mật khẩu cần ít nhất 8 ký tự, gồm chữ hoa, chữ thường và số.
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label
                    htmlFor="new-password"
                    className="block text-sm font-medium text-mocha mb-1.5 font-body"
                  >
                    Mật khẩu mới
                  </label>
                  <div className="relative">
                    <input
                      id="new-password"
                      type={showPassword ? "text" : "password"}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                      minLength={8}
                      autoComplete="new-password"
                      placeholder="Nhập mật khẩu mới"
                      className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-200 focus:border-pink-pastel focus:ring-2 focus:ring-pink-pastel/20 outline-none transition-colors font-body text-mocha placeholder:text-gray-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-mocha/50 hover:text-mocha transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                      aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                    >
                      {showPassword ? (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12c1.292 4.338 5.31 7.5 10.066 7.5.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                        </svg>
                      ) : (
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                          <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="confirm-password"
                    className="block text-sm font-medium text-mocha mb-1.5 font-body"
                  >
                    Xác nhận mật khẩu mới
                  </label>
                  <input
                    id="confirm-password"
                    type={showPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={8}
                    autoComplete="new-password"
                    placeholder="Nhập lại mật khẩu mới"
                    className={`w-full px-4 py-3 rounded-lg border focus:ring-2 outline-none transition-colors font-body text-mocha placeholder:text-gray-400 ${
                      confirmPassword && confirmPassword !== newPassword
                        ? "border-red-300 focus:border-red-400 focus:ring-red-200"
                        : "border-gray-200 focus:border-pink-pastel focus:ring-pink-pastel/20"
                    }`}
                  />
                  {confirmPassword && confirmPassword !== newPassword && (
                    <p className="mt-1 text-xs text-red-500">Mật khẩu không khớp</p>
                  )}
                </div>

                <button
                  type="submit"
                  id="reset-password-submit"
                  disabled={loading || !newPassword || newPassword !== confirmPassword}
                  className="w-full py-3 px-4 bg-pink-pastel text-white font-medium rounded-lg hover:bg-pink-pastel/90 focus:ring-2 focus:ring-pink-pastel/50 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-body min-h-[44px]"
                >
                  {loading ? "Đang cập nhật..." : "Đặt mật khẩu mới"}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

"use client";

/**
 * Forgot Password page.
 * User enters their email; backend sends a Supabase password reset email.
 * Always shows success to prevent email enumeration.
 */

import { Suspense, useState, FormEvent } from "react";
import Link from "next/link";
import { apiClient, ApiError } from "@/lib/api";

export default function ForgotPasswordPage() {
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
      <ForgotPasswordContent />
    </Suspense>
  );
}

function ForgotPasswordContent() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await apiClient.post("/api/v1/auth/forgot-password", { email });
      setSent(true);
    } catch (err: unknown) {
      const apiError = err as ApiError;
      const detail = apiError?.detail;
      if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Đã có lỗi xảy ra. Vui lòng thử lại.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream px-4 py-8">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🔑</div>
          <h1 className="text-3xl font-heading text-mocha mb-2">Quên mật khẩu?</h1>
          <p className="text-mocha/70 font-body">
            Nhập email đăng ký và chúng tôi sẽ gửi link khôi phục cho bạn
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          {sent ? (
            /* Success State */
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4.5 12.75l6 6 9-13.5"
                  />
                </svg>
              </div>
              <h2 className="text-xl font-heading text-mocha mb-2">Kiểm tra email của bạn!</h2>
              <p className="text-mocha/70 font-body text-sm mb-1">
                Chúng tôi đã gửi link khôi phục mật khẩu đến:
              </p>
              <p className="font-medium text-mocha mb-4">{email}</p>
              <p className="text-mocha/50 font-body text-xs mb-6">
                Không thấy email? Kiểm tra thư mục spam hoặc thử lại sau vài phút.
              </p>
              <button
                onClick={() => setSent(false)}
                className="text-sm text-pink-pastel hover:text-pink-pastel/80 font-medium transition-colors"
              >
                Gửi lại email khác
              </button>
            </div>
          ) : (
            /* Form State */
            <>
              {error && (
                <div
                  className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-body"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label
                    htmlFor="forgot-email"
                    className="block text-sm font-medium text-mocha mb-1.5 font-body"
                  >
                    Email đăng ký
                  </label>
                  <input
                    id="forgot-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    placeholder="email@example.com"
                    className="w-full px-4 py-3 rounded-lg border border-gray-200 focus:border-pink-pastel focus:ring-2 focus:ring-pink-pastel/20 outline-none transition-colors font-body text-mocha placeholder:text-gray-400"
                  />
                </div>

                <button
                  type="submit"
                  id="forgot-password-submit"
                  disabled={loading}
                  className="w-full py-3 px-4 bg-pink-pastel text-white font-medium rounded-lg hover:bg-pink-pastel/90 focus:ring-2 focus:ring-pink-pastel/50 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-body min-h-[44px]"
                >
                  {loading ? "Đang gửi..." : "Gửi link khôi phục"}
                </button>
              </form>
            </>
          )}

          <p className="mt-6 text-center text-sm text-mocha/70 font-body">
            Nhớ ra mật khẩu rồi?{" "}
            <Link
              href="/auth/login"
              className="text-pink-pastel hover:text-pink-pastel/80 font-medium transition-colors"
            >
              Đăng nhập
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

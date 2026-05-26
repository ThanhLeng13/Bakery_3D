"use client";

/**
 * Registration page with full validation.
 * Fields: email, password (show/hide), full name, phone (10 digits).
 * Inline validation errors matching backend format: {"detail": [{"field": "...", "message": "..."}]}
 */

import { Suspense, useState, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuthContext } from "@/contexts/AuthContext";
import { ApiError } from "@/lib/api";

interface FieldError {
  field: string;
  message: string;
}

export default function RegisterPage() {
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
      <RegisterContent />
    </Suspense>
  );
}

function RegisterContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { register } = useAuthContext();

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
    phone: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState("");
  const [loading, setLoading] = useState(false);

  const redirectUrl = searchParams.get("redirect") || "/";

  function updateField(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear field error on change
    if (fieldErrors[field]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  }

  function validateClient(): boolean {
    const errors: Record<string, string> = {};

    // Email validation
    if (!formData.email) {
      errors.email = "Vui lòng nhập email";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = "Email không hợp lệ";
    } else if (formData.email.length > 254) {
      errors.email = "Email không được quá 254 ký tự";
    }

    // Password validation
    if (!formData.password) {
      errors.password = "Vui lòng nhập mật khẩu";
    } else if (formData.password.length < 8) {
      errors.password = "Mật khẩu phải có ít nhất 8 ký tự";
    } else if (formData.password.length > 128) {
      errors.password = "Mật khẩu không được quá 128 ký tự";
    } else if (!/[A-Z]/.test(formData.password)) {
      errors.password = "Mật khẩu phải có ít nhất 1 chữ hoa";
    } else if (!/[a-z]/.test(formData.password)) {
      errors.password = "Mật khẩu phải có ít nhất 1 chữ thường";
    } else if (!/\d/.test(formData.password)) {
      errors.password = "Mật khẩu phải có ít nhất 1 chữ số";
    }

    // Full name validation
    if (!formData.full_name.trim()) {
      errors.full_name = "Vui lòng nhập họ tên";
    } else if (formData.full_name.length > 100) {
      errors.full_name = "Họ tên không được quá 100 ký tự";
    }

    // Phone validation
    if (!formData.phone) {
      errors.phone = "Vui lòng nhập số điện thoại";
    } else if (!/^\d{10}$/.test(formData.phone)) {
      errors.phone = "Số điện thoại phải đúng 10 chữ số";
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setGeneralError("");

    if (!validateClient()) return;

    setLoading(true);

    try {
      await register(formData);
      router.replace(redirectUrl);
    } catch (err: unknown) {
      const apiError = err as ApiError;

      if (Array.isArray(apiError.detail)) {
        // Backend validation errors: [{ field, message }]
        const errors: Record<string, string> = {};
        (apiError.detail as FieldError[]).forEach((e) => {
          errors[e.field] = e.message;
        });
        setFieldErrors(errors);
      } else if (typeof apiError.detail === "string") {
        setGeneralError(apiError.detail);
      } else {
        setGeneralError("Đã xảy ra lỗi, vui lòng thử lại sau");
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
          <h1 className="text-3xl font-heading text-mocha mb-2">Đăng ký</h1>
          <p className="text-mocha/70 font-body">
            Tạo tài khoản để đặt bánh kem
          </p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8">
          {/* General Error */}
          {generalError && (
            <div
              className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm font-body"
              role="alert"
            >
              {generalError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {/* Full Name */}
            <div>
              <label
                htmlFor="full_name"
                className="block text-sm font-medium text-mocha mb-1.5 font-body"
              >
                Họ và tên
              </label>
              <input
                id="full_name"
                type="text"
                value={formData.full_name}
                onChange={(e) => updateField("full_name", e.target.value)}
                autoComplete="name"
                placeholder="Nguyễn Văn A"
                className={`w-full px-4 py-3 rounded-lg border outline-none transition-colors font-body text-mocha placeholder:text-gray-400 ${
                  fieldErrors.full_name
                    ? "border-red-400 focus:border-red-400 focus:ring-2 focus:ring-red-200"
                    : "border-gray-200 focus:border-pink-pastel focus:ring-2 focus:ring-pink-pastel/20"
                }`}
              />
              {fieldErrors.full_name && (
                <p className="mt-1.5 text-sm text-red-600 font-body" role="alert">
                  {fieldErrors.full_name}
                </p>
              )}
            </div>

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-mocha mb-1.5 font-body"
              >
                Email
              </label>
              <input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => updateField("email", e.target.value)}
                autoComplete="email"
                placeholder="email@example.com"
                className={`w-full px-4 py-3 rounded-lg border outline-none transition-colors font-body text-mocha placeholder:text-gray-400 ${
                  fieldErrors.email
                    ? "border-red-400 focus:border-red-400 focus:ring-2 focus:ring-red-200"
                    : "border-gray-200 focus:border-pink-pastel focus:ring-2 focus:ring-pink-pastel/20"
                }`}
              />
              {fieldErrors.email && (
                <p className="mt-1.5 text-sm text-red-600 font-body" role="alert">
                  {fieldErrors.email}
                </p>
              )}
            </div>

            {/* Phone */}
            <div>
              <label
                htmlFor="phone"
                className="block text-sm font-medium text-mocha mb-1.5 font-body"
              >
                Số điện thoại
              </label>
              <input
                id="phone"
                type="tel"
                value={formData.phone}
                onChange={(e) => updateField("phone", e.target.value.replace(/\D/g, "").slice(0, 10))}
                autoComplete="tel"
                placeholder="0901234567"
                inputMode="numeric"
                className={`w-full px-4 py-3 rounded-lg border outline-none transition-colors font-body text-mocha placeholder:text-gray-400 ${
                  fieldErrors.phone
                    ? "border-red-400 focus:border-red-400 focus:ring-2 focus:ring-red-200"
                    : "border-gray-200 focus:border-pink-pastel focus:ring-2 focus:ring-pink-pastel/20"
                }`}
              />
              {fieldErrors.phone && (
                <p className="mt-1.5 text-sm text-red-600 font-body" role="alert">
                  {fieldErrors.phone}
                </p>
              )}
            </div>

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-mocha mb-1.5 font-body"
              >
                Mật khẩu
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) => updateField("password", e.target.value)}
                  autoComplete="new-password"
                  placeholder="Ít nhất 8 ký tự, 1 chữ hoa, 1 chữ thường, 1 số"
                  className={`w-full px-4 py-3 pr-12 rounded-lg border outline-none transition-colors font-body text-mocha placeholder:text-gray-400 ${
                    fieldErrors.password
                      ? "border-red-400 focus:border-red-400 focus:ring-2 focus:ring-red-200"
                      : "border-gray-200 focus:border-pink-pastel focus:ring-2 focus:ring-pink-pastel/20"
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-mocha/50 hover:text-mocha transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
                  aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                >
                  {showPassword ? (
                    <EyeOffIcon className="w-5 h-5" />
                  ) : (
                    <EyeIcon className="w-5 h-5" />
                  )}
                </button>
              </div>
              {fieldErrors.password && (
                <p className="mt-1.5 text-sm text-red-600 font-body" role="alert">
                  {fieldErrors.password}
                </p>
              )}
              {!fieldErrors.password && (
                <p className="mt-1.5 text-xs text-mocha/50 font-body">
                  Ít nhất 8 ký tự, bao gồm chữ hoa, chữ thường và số
                </p>
              )}
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-pink-pastel text-white font-medium rounded-lg hover:bg-pink-pastel/90 focus:ring-2 focus:ring-pink-pastel/50 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-body min-h-[44px]"
            >
              {loading ? "Đang đăng ký..." : "Đăng ký"}
            </button>
          </form>

          {/* Login Link */}
          <p className="mt-6 text-center text-sm text-mocha/70 font-body">
            Đã có tài khoản?{" "}
            <Link
              href={`/auth/login${redirectUrl !== "/" ? `?redirect=${encodeURIComponent(redirectUrl)}` : ""}`}
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

// --- Icons ---
function EyeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.98 8.223A10.477 10.477 0 001.934 12c1.292 4.338 5.31 7.5 10.066 7.5.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
      />
    </svg>
  );
}

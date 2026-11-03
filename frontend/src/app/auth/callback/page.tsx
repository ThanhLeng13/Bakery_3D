"use client";

/**
 * Trang nhận kết quả đăng nhập Google.
 *
 * Supabase chuyển về đây kèm phiên trong PHẦN FRAGMENT của URL:
 *   /auth/callback?redirect=/#access_token=...&refresh_token=...
 *
 * Bản cũ đọc `searchParams.get("access_token")` — tức đọc QUERY STRING, nên
 * luôn thấy null và báo "Không nhận được thông tin xác thực từ Google". Nó còn
 * gửi token đó vào `POST /api/v1/auth/oauth/google`, nơi backend gọi
 * `sign_in_with_id_token` và chờ một ID token của Google, không phải access
 * token của Supabase — hai thứ khác nhau nên cũng không khớp.
 *
 * Luồng đúng: Supabase đã xác thực xong và cấp sẵn phiên. Việc còn lại là lưu
 * token rồi hỏi `GET /api/v1/auth/me` để biết VAI, vì vai nằm ở bảng
 * `public.users` của tiệm chứ Supabase không giữ.
 */

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { AuthUser } from "@/lib/auth";
import { consumeOAuthState, readOAuthFragment } from "@/lib/google-oauth";
import { resolveLoginDestination } from "@/lib/roles";

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-surface">
          <div className="w-12 h-12 rounded-full border-4 border-brand border-t-transparent animate-spin" />
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}

function CallbackContent() {
  const searchParams = useSearchParams();
  const [error, setError] = useState("");
  // Chạy một lần. `searchParams` đổi tham chiếu giữa các lần render, nên để nó
  // trong deps sẽ khiến callback chạy lại và gọi /auth/me nhiều lần.
  const handled = useRef(false);

  useEffect(() => {
    if (handled.current) return;
    handled.current = true;

    async function handleCallback() {
      const redirectUrl = searchParams.get("redirect") || "/";
      const { accessToken, refreshToken, error: oauthError } =
        readOAuthFragment(window.location.hash);

      // Xoá fragment NGAY sau khi đọc, trước mọi `await`.
      //
      // Làm sau khi gọi /auth/me thì token còn nằm trên thanh địa chỉ suốt thời
      // gian chờ, và nếu lỗi thì nằm lại vĩnh viễn — vào lịch sử trình duyệt và
      // dễ bị chia sẻ qua ảnh chụp màn hình. Giữ nguyên path + query để
      // `searchParams` phía trên vẫn đúng.
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );

      if (oauthError) {
        // Nói đúng lỗi Supabase trả về (ví dụ provider Google chưa bật trong
        // Dashboard) thay vì một câu chung không giúp sửa được gì.
        setError(`Google trả về lỗi: ${oauthError}`);
        return;
      }

      // Đối chiếu `state` TRƯỚC khi lưu bất kỳ token nào.
      //
      // Luồng implicit nhận token từ fragment, nên trang này tin bất cứ ai mở
      // được URL. Không kiểm `state` thì kẻ tấn công dụ khách mở
      // `/auth/callback#access_token=<token của họ>` là khách bị đăng nhập vào
      // tài khoản của họ, và mọi đơn khách đặt sau đó nằm ở tài khoản đó.
      if (!consumeOAuthState(searchParams.get("state"))) {
        setError(
          "Yêu cầu đăng nhập không hợp lệ hoặc đã hết hiệu lực. " +
            "Vui lòng bấm đăng nhập Google lại từ trang đăng nhập.",
        );
        return;
      }

      if (!accessToken) {
        setError("Không nhận được thông tin xác thực từ Google");
        return;
      }

      try {
        // Lưu token TRƯỚC khi gọi /auth/me: apiClient đọc access_token từ
        // localStorage để đặt header Authorization.
        localStorage.setItem("access_token", accessToken);
        if (refreshToken) {
          localStorage.setItem("refresh_token", refreshToken);
        }

        // Vai nằm ở bảng `users` của tiệm. Endpoint này cũng tự tạo dòng hồ sơ
        // khi người dùng đăng nhập Google lần đầu.
        const user = await apiClient.get<AuthUser>("/api/v1/auth/me");
        localStorage.setItem("auth_user", JSON.stringify(user));

        // Điều hướng CỨNG, không dùng `router.replace`.
        //
        // `AuthContext` chỉ đặt `user` khi khởi tạo, khi gọi `login`/`register`,
        // hoặc khi nhận sự kiện `storage` — mà sự kiện đó KHÔNG kích hoạt trong
        // chính tab đã ghi. Trang này ghi localStorage trực tiếp, nên sau một
        // lần `router.replace` (điều hướng phía client) provider không remount
        // và `user` vẫn là null: `ProtectedRoute` thấy chưa đăng nhập và đẩy
        // khách về trang đăng nhập — đăng nhập Google trông như thất bại.
        //
        // Tải lại trang làm `initAuth` đọc lại localStorage, dựng phiên và bật
        // tự động làm mới token.
        window.location.assign(resolveLoginDestination(user.role, redirectUrl));
      } catch {
        // Dọn token nửa vời: giữ lại sẽ làm các trang sau tưởng đã đăng nhập.
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("auth_user");
        setError("Đăng nhập bằng Google thất bại. Vui lòng thử lại.");
      }
    }

    handleCallback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface px-4">
        <div className="text-center">
          <div
            id="callback-error"
            role="alert"
            className="mb-4 p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 font-body"
          >
            {error}
          </div>
          <a
            href="/auth/login"
            className="text-ink hover:text-ink font-medium font-body transition-colors"
          >
            Quay lại trang đăng nhập
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 rounded-full border-4 border-brand border-t-transparent animate-spin" />
        <p className="text-muted font-body">Đang xác thực...</p>
      </div>
    </div>
  );
}

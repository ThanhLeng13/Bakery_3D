/**
 * Đăng nhập Google qua Supabase Auth (luồng implicit, không cần SDK).
 *
 * Vì sao viết lại
 * ---------------
 * Nút "Đăng nhập bằng Google" trước đây chuyển hướng tới
 * `${API_URL}/api/v1/auth/oauth/google/redirect`. Endpoint đó KHÔNG tồn tại —
 * router backend chỉ có `POST /api/v1/auth/oauth/google`. Bấm nút là ra 404,
 * nên nút chưa bao giờ hoạt động.
 *
 * Luồng mới dùng chính Supabase, nơi dự án đã có khoá công khai:
 *
 *   1. Chuyển hướng trình duyệt tới `${SUPABASE_URL}/auth/v1/authorize?provider=google`
 *   2. Supabase lo toàn bộ phần bắt tay với Google
 *   3. Supabase chuyển về `redirect_to` kèm phiên trong PHẦN FRAGMENT của URL:
 *      `#access_token=...&refresh_token=...`
 *   4. Trang callback đọc fragment, lưu token, rồi gọi `GET /api/v1/auth/me`
 *      để lấy vai (vai nằm ở bảng `public.users`, Supabase không biết).
 *
 * Không thêm thư viện nào: `@supabase/supabase-js` không có trong package.json,
 * và luồng này chỉ là một lần chuyển hướng.
 *
 * ĐIỀU KIỆN BÊN NGOÀI CODE: provider Google phải được bật trong Supabase
 * Dashboard (Authentication -> Providers -> Google) và URL callback phải nằm
 * trong danh sách Redirect URLs. Không bật thì Supabase trả lỗi
 * `provider is not enabled` — code không thể tự làm thay.
 */

/** Token Supabase trả về trong fragment sau khi đăng nhập Google xong. */
export interface OAuthFragmentTokens {
  accessToken: string | null;
  refreshToken: string | null;
  /** Thông báo lỗi Supabase trả về, nếu có (ví dụ provider chưa bật). */
  error: string | null;
}

/**
 * Đọc token từ fragment (`#...`) của URL hiện tại.
 *
 * Supabase trả phiên trong FRAGMENT, không phải query string. Đây là chỗ trang
 * callback cũ bị sai: nó đọc `searchParams.get("access_token")` nên luôn thấy
 * null và báo "Không nhận được thông tin xác thực từ Google".
 *
 * Fragment không được gửi lên server, nên token không lọt vào log truy cập.
 */
export function readOAuthFragment(hash: string): OAuthFragmentTokens {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  const params = new URLSearchParams(raw);

  const errorDescription = params.get("error_description");
  const error = params.get("error");

  return {
    accessToken: params.get("access_token"),
    refreshToken: params.get("refresh_token"),
    error: errorDescription || error || null,
  };
}

/**
 * URL để bắt đầu đăng nhập Google.
 *
 * @param callbackUrl URL tuyệt đối mà Supabase sẽ chuyển về sau khi xong.
 * @throws Error khi thiếu `NEXT_PUBLIC_SUPABASE_URL` — hỏng cấu hình thì phải
 *   nói rõ, thay vì chuyển hướng tới `undefined/auth/v1/authorize`.
 */
export function buildGoogleOAuthUrl(callbackUrl: string): string {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  if (!supabaseUrl) {
    throw new Error(
      "Thiếu NEXT_PUBLIC_SUPABASE_URL nên không thể đăng nhập bằng Google.",
    );
  }

  const base = supabaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams({
    provider: "google",
    redirect_to: callbackUrl,
  });

  return `${base}/auth/v1/authorize?${params.toString()}`;
}

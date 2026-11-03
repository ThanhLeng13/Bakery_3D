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
 * ĐIỀU KIỆN BÊN NGOÀI CODE
 * ------------------------
 * 1. Bật provider Google: Supabase Dashboard -> Authentication -> Providers ->
 *    Google. Chưa bật thì Supabase trả `provider is not enabled`, và trang
 *    callback in đúng lỗi đó.
 *
 * 2. Khai Redirect URLs có WILDCARD. Đây là chỗ dễ sai nhất và hỏng **im
 *    lặng**: `redirect_to` phải khớp danh sách Redirect URLs, và khi không
 *    khớp Supabase KHÔNG báo lỗi — nó chuyển về Site URL. Khách bấm đăng nhập
 *    Google, quay về trang chủ trong trạng thái chưa đăng nhập, và không có
 *    thông báo nào để lần ra nguyên nhân.
 *
 *    `redirect_to` do hàm này sinh LUÔN có query string (`redirect` và
 *    `state`), nên một entry khớp chính xác `/auth/callback` là KHÔNG đủ.
 *    Theo tài liệu Supabase, ký tự phân tách là `.` và `/`; `*` chỉ khớp chuỗi
 *    không chứa ký tự phân tách, còn `**` khớp mọi chuỗi. Vì vậy phải dùng
 *    `**`:
 *
 *      Site URL (để riêng, dùng cho link trong email):
 *        https://ten-mien-that.com
 *
 *      Redirect URLs — mỗi origin có thể nhận callback đều cần một dòng:
 *        https://ten-mien-that.com/auth/callback**
 *        http://localhost:3000/auth/callback**
 *        https://*-<team-slug>.vercel.app/auth/callback**   (bản preview)
 *
 *    Cổng localhost phải khớp cổng đang chạy. Bản preview của Vercel đổi tên
 *    miền mỗi lần deploy nên bắt buộc dùng wildcard, không khai tay từng bản.
 *
 * Tài liệu: https://supabase.com/docs/guides/auth/redirect-urls
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
 * Khoá lưu giá trị `state` dùng một lần, để chống đăng nhập bị giả mạo.
 *
 * Luồng implicit trả token trong fragment, nên trang callback nhận token từ
 * bất cứ ai mở được URL đó. Không có `state`, kẻ tấn công chỉ cần dụ khách mở
 * `/auth/callback#access_token=<token của kẻ tấn công>` là khách bị đăng nhập
 * vào tài khoản của họ — mọi đơn khách đặt sau đó nằm trong tài khoản kẻ tấn
 * công.
 *
 * `sessionStorage` chứ không phải `localStorage`: giá trị chỉ cần sống trong
 * một tab, một lần đăng nhập.
 */
const OAUTH_STATE_KEY = "bakery_oauth_state";

/** Sinh giá trị `state` khó đoán và lưu lại để đối chiếu khi Supabase trả về. */
function createOAuthState(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  const state = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  sessionStorage.setItem(OAUTH_STATE_KEY, state);
  return state;
}

/**
 * Đối chiếu `state` rồi XOÁ ngay, nên mỗi giá trị chỉ dùng được một lần.
 *
 * @returns true khi khớp. Thiếu hoặc lệch đều trả false.
 */
export function consumeOAuthState(received: string | null): boolean {
  let expected: string | null = null;
  try {
    expected = sessionStorage.getItem(OAUTH_STATE_KEY);
    sessionStorage.removeItem(OAUTH_STATE_KEY);
  } catch {
    return false;
  }
  if (!expected || !received) return false;
  return expected === received;
}

/**
 * URL để bắt đầu đăng nhập Google.
 *
 * @param callbackUrl URL tuyệt đối mà Supabase sẽ chuyển về sau khi xong. Hàm
 *   này tự gắn thêm `state` vào đó; Supabase giữ nguyên query string của
 *   `redirect_to` khi chuyển về.
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

  const callback = new URL(callbackUrl);
  callback.searchParams.set("state", createOAuthState());

  const base = supabaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams({
    provider: "google",
    redirect_to: callback.toString(),
  });

  return `${base}/auth/v1/authorize?${params.toString()}`;
}

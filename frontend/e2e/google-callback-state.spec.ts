import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Trang callback Google phải đối chiếu `state` — và phải cho qua khi khớp.
 *
 * Luồng implicit nhận token từ FRAGMENT của URL, nên trang này tin bất cứ ai mở
 * được đường dẫn đó. Không kiểm `state`, kẻ tấn công chỉ cần dụ khách mở
 * `/auth/callback#access_token=<token của họ>` là khách bị đăng nhập vào tài
 * khoản của họ, và mọi đơn khách đặt sau đó nằm ở tài khoản đó.
 *
 * Thêm phép kiểm thì rủi ro ngược lại xuất hiện: nếu `state` không bao giờ
 * khớp thì KHÔNG AI đăng nhập Google được nữa. Vì vậy test cả hai chiều.
 *
 * Cách kiểm trường hợp THÀNH CÔNG
 * -------------------------------
 * Không đọc localStorage sau khi điều hướng xong. Trang đích chạy
 * `AuthContext.initAuth`, và vì token giả không phải JWT hợp lệ nên nó gọi
 * `/api/v1/auth/refresh`; `isolateNetwork` trả fixture rỗng kèm 200, rồi
 * `storeAuthData` ghi `undefined` lên cả ba khoá. Đó là hành vi của trang đích,
 * không phải của callback. Vì vậy ta kiểm điều callback THẬT SỰ làm: nó gửi
 * `/auth/me` kèm đúng token Supabase trong header `Authorization`.
 */

const ACCESS_TOKEN = "tok-abc";
const FRAGMENT = `#access_token=${ACCESS_TOKEN}&refresh_token=ref-abc&token_type=bearer`;
const STATE_KEY = "bakery_oauth_state";
const ERROR_BOX = "#callback-error";

/** Ghi lại mọi lần gọi `/auth/me` kèm header `Authorization`. */
async function stubAuthMe(page: import("@playwright/test").Page) {
  const calls: Array<{ auth: string | undefined }> = [];
  await page.route("**/api/v1/auth/me", (route) => {
    calls.push({ auth: route.request().headers()["authorization"] });
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "u1",
        email: "khach@example.test",
        full_name: "Khách Google",
        phone: null,
        role: "customer",
      }),
    });
  });
  return calls;
}

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

test("thiếu state: từ chối và KHÔNG lưu token", async ({ page }) => {
  const meCalls = await stubAuthMe(page);

  await page.goto(`/auth/callback?redirect=%2F${FRAGMENT}`);

  await expect(page.locator(ERROR_BOX)).toContainText(
    /không hợp lệ|hết hiệu lực/i,
  );

  // Phải chặn TRƯỚC khi lưu bất kỳ token nào.
  const stored = await page.evaluate(() => ({
    access: localStorage.getItem("access_token"),
    user: localStorage.getItem("auth_user"),
  }));
  expect(stored.access, "token bị lưu dù state không hợp lệ").toBeNull();
  expect(stored.user).toBeNull();
  expect(meCalls, "không được gọi /auth/me khi state không hợp lệ").toEqual([]);
});

test("state lệch: từ chối", async ({ page }) => {
  const meCalls = await stubAuthMe(page);
  await page.addInitScript((key: string) => {
    sessionStorage.setItem(key, "state-dung");
  }, STATE_KEY);

  await page.goto(`/auth/callback?redirect=%2F&state=state-sai${FRAGMENT}`);

  await expect(page.locator(ERROR_BOX)).toBeVisible();
  await expect(
    page.evaluate(() => localStorage.getItem("access_token")),
  ).resolves.toBeNull();
  expect(meCalls).toEqual([]);
});

test("state khớp: dùng đúng token để gọi /auth/me và xoá token khỏi URL", async ({
  page,
}) => {
  const meCalls = await stubAuthMe(page);
  await page.addInitScript((key: string) => {
    sessionStorage.setItem(key, "state-khop");
  }, STATE_KEY);

  await page.goto(`/auth/callback?redirect=%2F&state=state-khop${FRAGMENT}`);

  // Phép kiểm chính: state khớp thì callback đi tiếp và dùng token Supabase.
  await expect.poll(() => meCalls.length, { timeout: 20_000 }).toBe(1);
  expect(meCalls[0].auth).toBe(`Bearer ${ACCESS_TOKEN}`);

  // Thành công thì điều hướng cứng sang đích — cần thiết vì `AuthContext` chỉ
  // đọc lại localStorage khi khởi tạo, không nhận sự kiện `storage` trong cùng
  // tab, nên `router.replace` sẽ để `ProtectedRoute` tưởng chưa đăng nhập.
  await page.waitForURL((url) => !url.pathname.startsWith("/auth/callback"), {
    timeout: 20_000,
  });

  // Token không được còn trên URL.
  expect(page.url()).not.toContain("access_token");
});

test("token bị xoá khỏi URL ngay cả khi /auth/me lỗi", async ({ page }) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({ status: 500, contentType: "application/json", body: "{}" }),
  );
  await page.addInitScript((key: string) => {
    sessionStorage.setItem(key, "state-khop");
  }, STATE_KEY);

  await page.goto(`/auth/callback?redirect=%2F&state=state-khop${FRAGMENT}`);

  await expect(page.locator(ERROR_BOX)).toBeVisible();

  // Dọn fragment phải xảy ra TRƯỚC `await`, nếu không token nằm lại trên thanh
  // địa chỉ và vào lịch sử trình duyệt.
  expect(page.url()).not.toContain("access_token");

  // Và không được để lại token nửa vời, vì các trang sau sẽ tưởng đã đăng nhập.
  const stored = await page.evaluate(() => ({
    access: localStorage.getItem("access_token"),
    user: localStorage.getItem("auth_user"),
  }));
  expect(stored.access).toBeNull();
  expect(stored.user).toBeNull();
});

test("state dùng một lần: phát lại URL cũ là bị từ chối", async ({ page }) => {
  const meCalls = await stubAuthMe(page);

  // KHÔNG dùng `addInitScript` ở đây: nó chạy lại trên MỌI lần điều hướng, nên
  // sẽ nạp lại `state` và lần phát lại thứ hai vẫn khớp — test sẽ xanh một
  // cách vô nghĩa. Đặt một lần, trên một trang đã tải.
  await page.goto("/auth/login");
  await page.evaluate(
    (arg: { key: string; value: string }) =>
      sessionStorage.setItem(arg.key, arg.value),
    { key: STATE_KEY, value: "state-mot-lan" },
  );

  const url = `/auth/callback?redirect=%2F&state=state-mot-lan${FRAGMENT}`;

  await page.goto(url);
  await expect.poll(() => meCalls.length, { timeout: 20_000 }).toBe(1);

  // Chờ lần đăng nhập đầu điều hướng XONG trước khi phát lại.
  //
  // Thành công thì callback chạy `window.location.assign`. Nếu `goto` thứ hai
  // chen vào trước lúc đó, lần assign đang chờ sẽ kéo trình duyệt sang trang
  // đích và test đi tìm thông báo lỗi trên sai trang.
  await page.waitForURL((u) => !u.pathname.startsWith("/auth/callback"), {
    timeout: 20_000,
  });

  // Phát lại đúng URL đó. `consumeOAuthState` đã xoá giá trị sau lần đầu, nên
  // lần này phải bị từ chối — không cần can thiệp gì thêm.
  await page.goto(url);

  await expect(page.locator(ERROR_BOX)).toBeVisible();
  expect(meCalls.length, "URL phát lại không được đăng nhập lần nữa").toBe(1);
});

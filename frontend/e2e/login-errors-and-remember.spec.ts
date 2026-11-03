import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Trang đăng nhập phải nói đúng lý do thất bại, và không tự tải lại trang.
 *
 * Người dùng báo: "đăng nhập không được mặc dù tôi đã đúng mật khẩu".
 *
 * Có ba lỗi chồng lên nhau, cả ba đều kết thúc bằng cùng một câu "Email hoặc
 * mật khẩu không đúng":
 *
 *   1. `auth_service.login` đọc `user_result.data` trong khi `maybe_single()`
 *      trả None khi thiếu dòng `public.users` -> AttributeError -> 401.
 *   2. `UserResponse.full_name`/`email` khai `str` bắt buộc, còn code dùng
 *      `.get("full_name", "")` — giá trị mặc định không áp dụng cho cột NULL,
 *      nên trả None và FastAPI validate response thất bại -> 500.
 *   3. `apiClient` chạy interceptor 401 TOÀN CỤC cho cả request đăng nhập:
 *      `handle401` xoá token rồi `window.location.href = "/auth/login"`, tức
 *      tải lại trang và xoá thông báo lỗi vừa đặt. Nó còn thay lỗi thật bằng
 *      `Error("Unauthorized")` nên nơi gọi mất `detail` và `retry_after`.
 *
 * Hai lỗi đầu đã có test ở `backend/tests/test_login_failure_causes.py`. File
 * này canh lỗi thứ ba cùng phần thông báo, vì chúng chỉ quan sát được khi trang
 * chạy thật.
 */

const LOGIN_URL = "**/api/v1/auth/login";

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

async function fillAndSubmit(page: import("@playwright/test").Page) {
  await page.locator("#email").fill("admin@example.test");
  await page.locator("#password").fill("MatKhauDung123!");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();
}

test("mật khẩu sai: hiện lỗi và KHÔNG tải lại trang", async ({ page }) => {
  await page.route(LOGIN_URL, (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Invalid email or password" }),
    }),
  );

  await page.goto("/auth/login");

  // Đánh dấu vào window: nếu trang bị tải lại thì dấu này mất.
  await page.evaluate(() => {
    (window as unknown as { __kept?: boolean }).__kept = true;
  });

  await fillAndSubmit(page);

  await expect(page.locator("#login-error")).toContainText(
    "Email hoặc mật khẩu không đúng",
  );

  // Interceptor 401 cũ chạy `window.location.href = "/auth/login"` nên trang
  // tải lại và thông báo biến mất ngay sau khi hiện.
  const kept = await page.evaluate(
    () => (window as unknown as { __kept?: boolean }).__kept === true,
  );
  expect(kept, "trang đăng nhập bị tải lại sau khi đăng nhập thất bại").toBe(
    true,
  );
});

test("lỗi server 500: không được nói là sai mật khẩu", async ({ page }) => {
  await page.route(LOGIN_URL, (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Internal Server Error" }),
    }),
  );

  await page.goto("/auth/login");
  await fillAndSubmit(page);

  const alert = page.locator("#login-error");
  await expect(alert).toBeVisible();
  // Đây chính là trường hợp người dùng gặp: mật khẩu đúng, server lỗi vì dữ
  // liệu NULL, mà giao diện lại quy cho mật khẩu.
  await expect(alert).not.toContainText("Email hoặc mật khẩu không đúng");
  await expect(alert).toContainText(/Máy chủ/i);
});

test("bị khoá tạm thời: hiện số phút phải chờ", async ({ page }) => {
  await page.route(LOGIN_URL, (route) =>
    route.fulfill({
      status: 429,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "Too many attempts. Please try again later.",
        retry_after: 900,
      }),
    }),
  );

  await page.goto("/auth/login");
  await fillAndSubmit(page);

  await expect(page.locator("#login-error")).toContainText("15 phút");
});

test("nhớ đăng nhập: điền lại email ở lần sau, không lưu mật khẩu", async ({
  page,
}) => {
  await page.route(LOGIN_URL, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "tok",
        refresh_token: "ref",
        token_type: "bearer",
        expires_in: 3600,
        user: {
          id: "u1",
          email: "admin@example.test",
          full_name: "Quản trị",
          phone: null,
          role: "customer",
        },
      }),
    }),
  );

  await page.goto("/auth/login");
  await page.locator("#remember-me").check();
  await fillAndSubmit(page);

  // Rời trang rồi quay lại: email phải được điền sẵn.
  await page.goto("/auth/login");
  await expect(page.locator("#email")).toHaveValue("admin@example.test");
  await expect(page.locator("#remember-me")).toBeChecked();

  // Mật khẩu KHÔNG được lưu ở bất kỳ khoá localStorage nào.
  const leaked = await page.evaluate(() => {
    const out: string[] = [];
    for (let i = 0; i < localStorage.length; i += 1) {
      const key = localStorage.key(i);
      if (!key) continue;
      if ((localStorage.getItem(key) ?? "").includes("MatKhauDung123!")) {
        out.push(key);
      }
    }
    return out;
  });
  expect(leaked, "mật khẩu bị lưu vào localStorage").toEqual([]);
});

test("bỏ chọn nhớ đăng nhập thì xoá email đã lưu", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("bakery_remembered_email", "cu@example.test");
  });
  await page.route(LOGIN_URL, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        access_token: "tok",
        refresh_token: "ref",
        token_type: "bearer",
        expires_in: 3600,
        user: {
          id: "u1",
          email: "moi@example.test",
          full_name: "",
          phone: null,
          role: "customer",
        },
      }),
    }),
  );

  await page.goto("/auth/login");
  await expect(page.locator("#email")).toHaveValue("cu@example.test");

  await page.locator("#remember-me").uncheck();
  await page.locator("#email").fill("moi@example.test");
  await page.locator("#password").fill("MatKhauDung123!");
  await page.getByRole("button", { name: "Đăng nhập", exact: true }).click();

  await expect
    .poll(() =>
      page.evaluate(() => localStorage.getItem("bakery_remembered_email")),
    )
    .toBeNull();
});

test("nút Google đi tới Supabase, không tới endpoint backend không tồn tại", async ({
  page,
}) => {
  await page.goto("/auth/login");

  const attempts: string[] = [];
  // Chặn mọi điều hướng để đọc đích mà không thật sự rời trang.
  await page.route("**/auth/v1/authorize**", (route) => {
    attempts.push(route.request().url());
    return route.abort();
  });
  await page.route("**/api/v1/auth/oauth/google/redirect**", (route) => {
    attempts.push(route.request().url());
    return route.abort();
  });

  await page.getByRole("button", { name: /Google/i }).click();
  await page.waitForTimeout(1500);

  expect(attempts.length, "nút Google không chuyển hướng đi đâu").toBeGreaterThan(
    0,
  );
  // Endpoint cũ không tồn tại trong router backend -> luôn 404.
  expect(attempts.join(" ")).not.toContain("/api/v1/auth/oauth/google/redirect");
  expect(attempts.join(" ")).toContain("/auth/v1/authorize");
  expect(attempts.join(" ")).toContain("provider=google");
});

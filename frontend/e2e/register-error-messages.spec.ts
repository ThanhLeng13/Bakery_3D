import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Trang đăng ký phải LUÔN hiện một thông báo dùng được.
 *
 * Người dùng báo: tạo tài khoản thì chỉ thấy "Đã xảy ra lỗi, vui lòng thử lại
 * sau". Đo từng dạng phản hồi cho thấy hai vấn đề khác nhau:
 *
 *   - `detail` dạng {loc, msg, type} — tức dạng CHÍNH FastAPI trả khi dữ liệu
 *     không hợp lệ — làm form KHÔNG hiện gì cả, vì trang chỉ đọc `e.field` và
 *     `e.message`. Đây là lỗi im lặng, tệ hơn một thông báo sai.
 *   - `fetch` thất bại vì không gọi được máy chủ cũng ra đúng câu chung chung
 *     đó, nên người dùng không biết nguyên nhân thật là máy chủ chưa chạy.
 *
 * Hai mốc quan trọng nhất cần giữ: KHÔNG được im lặng, và lỗi mạng phải nói rõ
 * là lỗi mạng.
 */

const FORM = {
  full_name: "Nguyen Van Test",
  email: "test.dangky@gmail.com",
  phone: "0912345678",
  password: "Matkhau1!",
};

async function dienVaGui(page: import("@playwright/test").Page) {
  await page.goto("/auth/register");
  await page.fill("#full_name", FORM.full_name);
  await page.fill("#email", FORM.email);
  await page.fill("#phone", FORM.phone);
  await page.fill("#password", FORM.password);
  const confirm = page.locator("#confirm_password");
  if (await confirm.count()) await confirm.fill(FORM.password);
  await page.click('button[type="submit"]');
}

/** Mọi chữ đỏ đang hiện trên trang, gộp lại. */
async function chuLoi(page: import("@playwright/test").Page): Promise<string> {
  const texts = await page
    .locator('[role="alert"], .text-red-600, .text-red-700, .text-red-500')
    .allInnerTexts();
  return texts.join(" | ").trim();
}

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

test("mất kết nối máy chủ: nói rõ là lỗi kết nối, không nói chung chung", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/register", (r) => r.abort("connectionrefused"));
  await dienVaGui(page);

  await expect
    .poll(() => chuLoi(page), { timeout: 15_000 })
    .toMatch(/không kết nối được tới máy chủ/i);

  // Không được quy sai cho người dùng khi lỗi nằm ở phía hệ thống.
  expect(await chuLoi(page)).not.toMatch(/không hợp lệ|đã được sử dụng/i);
});

test("422 dạng gốc FastAPI: phải hiện lỗi, KHÔNG được im lặng", async ({ page }) => {
  await page.route("**/api/v1/auth/register", (r) =>
    r.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        detail: [
          {
            type: "string_too_short",
            loc: ["body", "password"],
            msg: "String should have at least 8 characters",
          },
        ],
      }),
    }),
  );
  await dienVaGui(page);

  const loi = await (async () => {
    await expect.poll(() => chuLoi(page), { timeout: 15_000 }).not.toBe("");
    return chuLoi(page);
  })();

  expect(loi, "lỗi kiểm tra dữ liệu của FastAPI bị bỏ im lặng").not.toBe("");
  expect(loi).toMatch(/mật khẩu/i);
  expect(loi).toMatch(/8/);
});

test("422 thiếu trường: hiện tên trường bằng tiếng Việt", async ({ page }) => {
  await page.route("**/api/v1/auth/register", (r) =>
    r.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        detail: [{ type: "missing", loc: ["body", "phone"], msg: "Field required" }],
      }),
    }),
  );
  await dienVaGui(page);

  await expect
    .poll(() => chuLoi(page), { timeout: 15_000 })
    .toMatch(/số điện thoại/i);
});

test("422 dạng {field,message} của tầng dịch vụ vẫn hoạt động", async ({ page }) => {
  await page.route("**/api/v1/auth/register", (r) =>
    r.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        detail: [{ field: "email", message: "Email is already registered" }],
      }),
    }),
  );
  await dienVaGui(page);

  await expect
    .poll(() => chuLoi(page), { timeout: 15_000 })
    .toMatch(/already registered/i);
});

test("500 với detail dạng chuỗi: hiện đúng nguyên văn", async ({ page }) => {
  await page.route("**/api/v1/auth/register", (r) =>
    r.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Registration failed" }),
    }),
  );
  await dienVaGui(page);

  await expect
    .poll(() => chuLoi(page), { timeout: 15_000 })
    .toMatch(/Registration failed/i);
});

test("phản hồi không phải JSON: vẫn có thông báo, không treo form", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/register", (r) =>
    r.fulfill({
      status: 502,
      contentType: "text/html",
      body: "<html><body>Bad Gateway</body></html>",
    }),
  );
  await dienVaGui(page);

  await expect.poll(() => chuLoi(page), { timeout: 15_000 }).not.toBe("");
});

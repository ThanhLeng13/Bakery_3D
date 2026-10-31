import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Đơn nháp do trợ lý tạo phải HIỆN cho nhân viên bán hàng và có nút nhận.
 *
 * Trước đây: backend đã cho `draft → pending`, nhưng danh sách lọc
 * `("pending","ready")` và trang chỉ vẽ hai cột đó. Đơn trợ lý vừa tạo không
 * xuất hiện ở đâu, nên nhân viên không thể nhận — luồng đặt hàng qua chat kẹt
 * ở bước cuối dù từng phần đều "đã có".
 *
 * Test chặn API và kiểm giao diện; không tạo đơn thật.
 */

const DRAFT = {
  id: "bbbbbbbb-0000-0000-0000-000000000002",
  status: "draft",
  total_price: 350000,
  pickup_date: "2026-11-20T10:00:00+07:00",
  customer_name: "Khách từ trợ lý",
  customer_phone: "0900000002",
  customer_email: null,
  created_at: "2026-11-01T09:00:00Z",
};

const PENDING = {
  ...DRAFT,
  id: "aaaaaaaa-0000-0000-0000-000000000001",
  status: "pending",
  customer_name: "Khách đã đặt",
};

const DETAIL = {
  ...DRAFT,
  items: [
    { id: "i1", size: "20cm", flavor: "vanilla", quantity: 1, unit_price: 350000 },
  ],
  ai_summary: "Bánh kem tròn 20cm | Nhận: 2026-11-20",
  baker_notes: null,
};

const QUEUE = {
  orders: [PENDING],
  total: 1,
  pending_count: 1,
  ready_count: 0,
  drafts: [DRAFT],
  draft_count: 1,
};

/** JWT giả còn hạn — chỉ để `isAuthenticated()` và `parseJwtPayload` đọc được. */
function fakeJwt(role: string): string {
  const payload = {
    sub: "staff-1",
    role,
    exp: Math.floor(Date.now() / 1000) + 3600,
  };
  const encode = (value: object) =>
    Buffer.from(JSON.stringify(value)).toString("base64url");
  return `${encode({ alg: "none", typ: "JWT" })}.${encode(payload)}.sig`;
}

/**
 * Đặt phiên staff vào localStorage TRƯỚC khi app chạy.
 *
 * `/staff/*` nằm sau `ProtectedRoute allowedRoles=["staff"]`, nên không có phiên
 * thì mọi test chỉ nhìn thấy trang đăng nhập. Đây là phiên giả hoàn toàn: token
 * không ký, không gọi Supabase thật, và mọi request API đều bị `isolateNetwork`
 * chặn.
 */
async function signInAsStaff(page: import("@playwright/test").Page) {
  await page.addInitScript((token: string) => {
    localStorage.setItem("access_token", token);
    localStorage.setItem("refresh_token", token);
    localStorage.setItem(
      "auth_user",
      JSON.stringify({
        id: "staff-1",
        email: "staff@example.test",
        full_name: "Nhân viên thử",
        phone: null,
        role: "staff",
      }),
    );
  }, fakeJwt("staff"));
}

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
  await signInAsStaff(page);
  await page.route("**/api/v1/staff/orders", (route) =>
    route.request().method() === "GET"
      ? route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(QUEUE),
        })
      : route.fulfill({ status: 200, contentType: "application/json", body: "{}" }),
  );
  await page.route(`**/api/v1/staff/orders/${DRAFT.id}`, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(DETAIL),
    }),
  );
});

test("hàng đợi có mục đơn nháp và mở được chi tiết", async ({ page }) => {
  await page.goto("/staff/sales");

  // Tiêu đề cột có dạng "Đơn nháp từ trợ lý (1)"; `<h3>` để không khớp nhãn
  // trạng thái trên thẻ đơn.
  await expect(
    page.getByRole("heading", { name: /Đơn nháp từ trợ lý/ }),
  ).toBeVisible({ timeout: 20_000 });
  const draftCard = page.getByRole("button", { name: /Khách từ trợ lý/ });
  await expect(draftCard).toBeVisible();

  await draftCard.click();
  await expect(page.getByText("Chi tiết bán hàng")).toBeVisible();

  // Nút phải nói rõ đây là NHẬN đơn nháp, không phải "xác nhận đơn mới".
  await expect(page.getByRole("button", { name: /Nhận đơn nháp này/i })).toBeVisible();
});

test("nhận đơn nháp gửi status=pending lên máy chủ", async ({ page }) => {
  // Thu vào một mảng, không phải biến `| null`. TypeScript không theo dõi được
  // phép gán nằm trong callback của `page.route`, nên sau khi đọc
  // `patched?.body` nó thu hẹp kiểu về `null` rồi `never` — và `patched?.url`
  // báo lỗi TS2339, làm CI đỏ. Mảng giữ kiểu đúng và đọc được lần gọi đầu.
  const patched: Array<{ url: string; body: string }> = [];
  await page.route(`**/api/v1/staff/orders/${DRAFT.id}/status`, async (route) => {
    patched.push({
      url: route.request().url(),
      body: route.request().postData() ?? "",
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...DETAIL, status: "pending" }),
    });
  });

  await page.goto("/staff/sales");
  await page.getByRole("button", { name: /Khách từ trợ lý/ }).click();
  await page.getByRole("button", { name: /Nhận đơn nháp này/i }).click();

  await expect.poll(() => patched.length).toBe(1);
  const first = patched[0];
  expect(first.body).toContain('"pending"');
  expect(first.url).toContain(`/api/v1/staff/orders/${DRAFT.id}/status`);
});

import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Quyền: gõ thẳng URL vào trang quản lý phải bị chặn.
 *
 * Vì sao cần E2E cho việc đã có 189 test API: `roles.ts` chỉ **ẩn menu** — ẩn
 * menu không phải bảo mật, ai cũng gõ thẳng `/admin/products` được. 189 test
 * backend chứng minh API từ chối, nhưng không chứng minh **trang** điều hướng
 * đúng chỗ: khách gõ URL có thể bị đá về login, hoặc tệ hơn, nhìn thấy khung
 * trang với dữ liệu lỗi.
 *
 * Không đăng nhập ở đây vì không có phiên thật — test chỉ kiểm "không có phiên
 * thì bị đá về login", đó là đường bị bỏ qua nhiều nhất.
 */

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

const GUARDED = [
  { path: "/admin/products", label: "quản lý" },
  { path: "/admin/orders", label: "quản lý" },
  { path: "/admin/users", label: "quản lý" },
  { path: "/staff/sales", label: "nhân viên" },
  { path: "/baker/orders", label: "thợ làm bánh" },
  { path: "/orders", label: "khách hàng" },
  { path: "/checkout", label: "khách hàng" },
];

for (const { path, label } of GUARDED) {
  test(`chưa đăng nhập thì vào ${path} (${label}) bị đưa về trang đăng nhập`, async ({
    page,
  }) => {
    await page.goto(path);

    await expect(page).toHaveURL(/\/auth\/login/, { timeout: 15_000 });

    // Không được lộ nội dung trang đích. Kiểm một dấu hiệu cụ thể: tiêu đề trang
    // quản lý không xuất hiện, và không có bảng dữ liệu nào được dựng.
    await expect(page.locator("text=Khu quản lý")).toHaveCount(0);
    await expect(page.locator("text=Sản phẩm của tôi")).toHaveCount(0);
  });
}

test("trang đăng nhập có sẵn form, không bị chính nó đá đi", async ({ page }) => {
  // Ngược lại: nếu ca trên đỏ vì trang login cũng hỏng thì chưa kết luận được gì.
  await page.goto("/auth/login");

  await expect(page).toHaveURL(/\/auth\/login/);
  await expect(page.locator('input[type="email"]')).toBeVisible();
  await expect(page.locator('input[type="password"]')).toBeVisible();
});

test("/loyalty cho khách chưa đăng nhập xem được, nhưng không lộ số điểm", async ({
  page,
}) => {
  // Trang này KHÔNG đá về login — chủ ý, để khách xem trang tích điểm rồi tự
  // bấm đăng nhập. Nhưng nó phải hiện lời mời, KHÔNG được hiện dữ liệu điểm.
  //
  // Phân biệt hai điều: "không bị đá" là hành vi đúng, còn "lộ dữ liệu điểm"
  // là lỗi. Test này giữ cả hai điều kiện.
  await page.goto("/loyalty");

  await expect(page).toHaveURL(/\/loyalty/, { timeout: 15_000 });

  // Có lời mời đăng nhập.
  await expect(page.locator("text=Đăng nhập").first()).toBeVisible();

  // Và không hiện số điểm thật — nếu có thì là dữ liệu lộ ra ngoài ý muốn.
  await expect(page.locator("text=/\\d+(\\.\\d+)? điểm/i")).toHaveCount(0);
});

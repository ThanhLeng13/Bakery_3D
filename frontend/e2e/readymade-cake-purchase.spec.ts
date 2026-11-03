import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Mua một chiếc bánh sinh nhật LÀM SẴN phải đi tới cùng.
 *
 * Người dùng báo hai lỗi dẫn về cùng một chỗ:
 *   - "tôi vào thử mua bánh thì không có nút để tôi mua"
 *   - "không đặt được đơn hàng và giỏ hàng"
 *
 * Nguyên nhân: trang chi tiết bánh sinh nhật chỉ có một `<Link href="/checkout">`
 * nhãn "Đặt hàng ngay". Link đó KHÔNG thêm gì vào giỏ, nên checkout thấy giỏ
 * rỗng và hiện "Giỏ hàng trống" — không có đường nào mua được bánh sinh nhật.
 *
 * Phạm vi test
 * ------------
 * `/products/[id]` là SERVER component: lần fetch đầu chạy ở phía Node, nên
 * `page.route` không chặn được và không thể dựng trang bánh trong test. Vì vậy
 * phần nút trên trang chi tiết được canh bằng kiểm tra cấu trúc ở
 * `backend/tests/test_readymade_cake_order.py::TestFrontendRoutesCakesToOrders`,
 * còn ở đây kiểm phần CHẠY THẬT được: giỏ có bánh sinh nhật thì checkout phải
 * đặt được đơn, gửi đúng `POST /api/v1/orders`, và cho nhận trong ngày.
 */

const CAKE_ID = "cccccccc-0000-0000-0000-000000000001";
const CAKE_NAME = "Bánh sinh nhật hoa tươi";
const CAKE_PRICE = 420000;

/** Món bánh sinh nhật trong giỏ, đúng hình dạng `CartItem` đã lưu. */
const CAKE_CART_ITEM = {
  cartKey: CAKE_ID,
  productId: CAKE_ID,
  productName: CAKE_NAME,
  imageUrl: null,
  unitPrice: CAKE_PRICE,
  quantity: 1,
  expiresAt: null,
  branchId: null,
  branchName: null,
  productType: "cake",
};

/** JWT giả còn hạn — chỉ để `isAuthenticated()` đọc được `exp`. */
function fakeJwt(role: string): string {
  const encode = (value: object) =>
    Buffer.from(JSON.stringify(value)).toString("base64url");
  return (
    `${encode({ alg: "none", typ: "JWT" })}.` +
    `${encode({ sub: "cust-1", role, exp: Math.floor(Date.now() / 1000) + 3600 })}.sig`
  );
}

/**
 * Nạp giỏ VÀ phiên khách trước khi app chạy.
 *
 * `/checkout` nằm sau `ProtectedRoute`, nên không có phiên thì test chỉ thấy
 * trang đăng nhập. Phiên này giả hoàn toàn: token không ký, và `isolateNetwork`
 * chặn mọi request ra ngoài.
 *
 * Nạp giỏ qua localStorage thay vì bấm nút trên `/products/[id]`, vì trang đó
 * là server component — lần fetch đầu chạy ở Node nên `page.route` không chặn
 * được.
 */
async function seedCart(
  page: import("@playwright/test").Page,
  items: unknown[],
) {
  await page.addInitScript(
    (arg: { cart: string; token: string }) => {
      localStorage.setItem("bakery_cart", arg.cart);
      localStorage.setItem("access_token", arg.token);
      localStorage.setItem("refresh_token", arg.token);
      localStorage.setItem(
        "auth_user",
        JSON.stringify({
          id: "cust-1",
          email: "khach@example.test",
          full_name: "Khách thử",
          phone: null,
          role: "customer",
        }),
      );
    },
    { cart: JSON.stringify(items), token: fakeJwt("customer") },
  );
}

function localDateTimeValue(offsetHours: number): string {
  const at = new Date(Date.now() + offsetHours * 3600_000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${at.getFullYear()}-${pad(at.getMonth() + 1)}-${pad(at.getDate())}` +
    `T${pad(at.getHours())}:${pad(at.getMinutes())}`
  );
}

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

test("giỏ có bánh sinh nhật thì checkout không báo 'Giỏ hàng trống'", async ({
  page,
}) => {
  await seedCart(page, [CAKE_CART_ITEM]);
  await page.goto("/checkout");

  // Trước khi sửa, bánh sinh nhật không bao giờ vào được giỏ, nên khách luôn
  // thấy màn hình này.
  await expect(page.getByText("Giỏ hàng trống")).toHaveCount(0);
  await expect(page.getByText(CAKE_NAME).first()).toBeVisible();
});

test("bánh làm sẵn có ô ngày nhận và không đòi chọn chi nhánh", async ({
  page,
}) => {
  await seedCart(page, [CAKE_CART_ITEM]);
  await page.goto("/checkout");

  // Ô ngày nhận trước đây chỉ render cho chế độ Studio, nên đơn bánh làm sẵn
  // bị chặn ở lỗi "Vui lòng chọn ngày nhận bánh" mà không có ô nào để nhập.
  await expect(page.locator("#pickupDate")).toBeVisible();

  // Tồn kho theo chi nhánh chỉ có cho bánh ngọt, nên bánh sinh nhật không có
  // chi nhánh để chọn; hiện cảnh báo đó là bắt khách đi tìm thứ không tồn tại.
  await expect(
    page.getByText(/quay lại trang sản phẩm và chọn chi nhánh/i),
  ).toHaveCount(0);
});

test("đặt bánh làm sẵn gọi /api/v1/orders và cho nhận trong ngày", async ({
  page,
}) => {
  const posts: Array<{ body: string }> = [];
  const wrongRoute: string[] = [];

  await page.route("**/api/v1/orders", async (route) => {
    posts.push({ body: route.request().postData() ?? "" });
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        id: "order-1",
        status: "pending",
        total_price: CAKE_PRICE,
        pickup_date: new Date(Date.now() + 3 * 3600_000).toISOString(),
        customer_name: "Khách thử",
        customer_phone: "0900000001",
      }),
    });
  });

  // Nếu giao diện gửi sai đường, request này sẽ xuất hiện. Server chặn mọi
  // `product_type != 'sweet'` ở /purchases, nên gửi sai là đơn hỏng.
  await page.route("**/api/v1/purchases", async (route) => {
    wrongRoute.push(route.request().url());
    await route.fulfill({ status: 400, body: "{}" });
  });

  await seedCart(page, [CAKE_CART_ITEM]);
  await page.goto("/checkout");

  await page.locator("#fullName").fill("Khách thử");
  await page.locator("#phone").fill("0900000001");
  // Nhận sau 3 giờ: hợp lệ với mẫu làm sẵn (0 giờ chờ). Mốc 24/48 giờ chỉ dành
  // cho mẫu đặt qua Studio.
  await page.locator("#pickupDate").fill(localDateTimeValue(3));

  await page
    .getByRole("button", { name: /Đặt hàng|Xác nhận/i })
    .first()
    .click();

  await expect.poll(() => posts.length, { timeout: 20_000 }).toBe(1);
  expect(wrongRoute, "bánh sinh nhật không được gửi vào /purchases").toEqual([]);

  const payload = JSON.parse(posts[0].body);
  expect(payload.items).toHaveLength(1);
  expect(payload.items[0].product_id).toBe(CAKE_ID);
  // Mẫu làm sẵn không có thiết kế riêng. Gửi `customization_json` vào sẽ khiến
  // server coi là mẫu đặt và đòi 24/48 giờ.
  expect(payload.items[0].customization_json).toBeUndefined();
});

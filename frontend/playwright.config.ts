import { defineConfig, devices, type Page, type Route } from "@playwright/test";

/**
 * Cấu hình E2E — chạy cô lập, KHÔNG tạo đơn thật.
 *
 * Nguyên tắc: mọi request ra ngoài (`/api/v1/**`, `*.supabase.co`) bị chặn và
 * trả dữ liệu giả. Lý do:
 *   - test CI không được đụng vào CSDL của tiệm, và không được tạo đơn thật;
 *   - chính những lần thử trước đã để lại rác trong `public.users` và
 *     `auth.users` — các tài khoản không đăng nhập được, phải dọn tay.
 *
 * Vì vậy test ở đây kiểm **hành vi giao diện**: trường nào bắt buộc, lỗi nào
 * hiện, quyền nào chặn — chứ không kiểm con số do máy chủ tính.
 */

const EMPTY_LIST = JSON.stringify([]);

/**Payload giả cho từng endpoint, để trang không trắng và không vỡ. */
function payloadFor(path: string): { status: number; body: string } {
  if (path.includes("/products")) {
    return {
      status: 200,
      body: JSON.stringify([
        {
          id: "11111111-1111-1111-1111-111111111111",
          name: "Bánh kem tròn 1 tầng",
          slug: "banh-kem-tron-1-tang",
          base_price: 350000,
          product_type: "cake",
          is_active: true,
          images: [],
          three_d_models: [],
        },
      ]),
    };
  }
  if (path.includes("/cake-3d-models")) {
    return {
      status: 200,
      body: JSON.stringify([
        {
          id: "22222222-2222-2222-2222-222222222222",
          name: "Tròn 1 tầng",
          glb_url: "/models/cake-tron-1-tang.glb",
        },
      ]),
    };
  }
  if (path.includes("/options")) {
    return {
      status: 200,
      body: JSON.stringify({
        sizes: [
          { id: "s1", name: "16cm", price_delta: 0 },
          { id: "s2", name: "20cm", price_delta: 50000 },
          { id: "s3", name: "24cm", price_delta: 120000 },
        ],
        flavors: [],
        toppings: [],
        decorations: [],
      }),
    };
  }
  return { status: 200, body: EMPTY_LIST };
}

/**
 * Chặn mọi request ra ngoài NGAY TỪ ĐẦU, kể cả khi một trang nào đó gọi API thật.
 * Dùng ở `beforeEach` của mỗi test, nên không test nào chạm internet được.
 */
export async function isolateNetwork(page: Page) {
  await page.route(/^https?:\/\/(?!localhost:\d+)/, (route: Route) => {
    const url = route.request().url();
    // Cho file tĩnh của Next đi qua (GLB, ảnh) vì nó cùng origin localhost.
    if (/\.(glb|png|jpe?g|svg|webp|woff2?)$/i.test(url)) {
      return route.continue();
    }
    const payload = payloadFor(new URL(url).pathname);
    return route.fulfill({
      status: payload.status,
      contentType: "application/json",
      body: payload.body,
    });
  });
}

export default defineConfig({
  testDir: "./e2e",
  // Cố ý chạy TUẦN TỰ, không `fullyParallel`.
  //
  // Lý do: các trang dùng chung `localStorage` (`cake_customization_json`,
  // `cartItems`, phiên đăng nhập). Playwright cho mỗi test một context riêng,
  // nhưng khi nhiều worker chạy song song thì trạng thái vốn đã lộn xộn — một
  // test xoá design lúc test khác đang cần. Đã đo: `cake-builder` 3 pass khi
  // chạy riêng, nhưng fail khi chạy cùng `checkout`.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "line" : "list",

  use: {
    baseURL: "http://localhost:3100",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },

  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],

  webServer: {
    command: "npx next start -p 3100",
    url: "http://localhost:3100",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
    env: {
      NEXT_PUBLIC_API_URL: "http://localhost:3100",
      NEXT_PUBLIC_SUPABASE_URL: "https://example.supabase.co",
      NEXT_PUBLIC_SUPABASE_ANON_KEY: "test-anon-key",
    },
  },
});

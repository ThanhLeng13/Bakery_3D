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
      // The endpoint returns `{ models: [...] }`, not a bare array. Serving an
      // array here made `models.map` throw at runtime, and the JS-error test
      // filtered that message away — so the fixture hid a real crash.
      body: JSON.stringify({
        models: [
          {
            id: "22222222-2222-2222-2222-222222222222",
            name: "Tròn 1 tầng",
            slug: "tron-1-tang",
            glb_url: "/models/cake-tron-1-tang.glb",
          },
        ],
      }),
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
 *
 * Phải chặn CẢ `localhost:<port khác>`: app gọi backend ở `localhost:8000`
 * (`NEXT_PUBLIC_API_URL` lúc build), nên nếu chỉ chặn host không phải localhost
 * thì đúng các lời gọi API thật lại lọt qua — test "cô lập" vẫn đọc CSDL của
 * tiệm. Chỉ origin của chính app (`localhost:3100`) và file tĩnh của nó được đi
 * tiếp.
 */
export async function isolateNetwork(page: Page) {
  const appOrigin = new URL("http://localhost:3100").origin;
  await page.route(/^https?:\/\//, (route: Route) => {
    const url = route.request().url();
    let origin = "";
    try {
      origin = new URL(url).origin;
    } catch {
      return route.abort();
    }
    if (origin === appOrigin) {
      // Trang và file tĩnh của Next (GLB, ảnh, font) đi qua bình thường.
      return route.continue();
    }
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
  // CI chỉ có 2 vCPU, máy dev thường 8+. Các trang này render 3D qua WebGL
  // và SSR gọi xuống backend, nên thời gian khởi động chiếm phần lớn thời
  // gian test. Đã đo trên máy 8 core: cả file `cake-builder` 31.7s, riêng test
  // topping 12.6s. Khi tạo tải CPU để mô phỏng 2 vCPU thì cả file lên 44.8s và
  // test topping 15.8s — vượt ngưỡng mặc định 30s của Playwright. Vì vậy CI
  // được cho 60s mỗi test.
  //
  // Lỗi thật đã gặp: CI báo `Test timeout of 30000ms exceeded` ở đúng test
  // topping, retry một lần vẫn hết hạn, trong khi trên máy dev pass liên tục.
  timeout: process.env.CI ? 60_000 : 30_000,

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

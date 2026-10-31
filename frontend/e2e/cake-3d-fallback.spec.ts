import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Canvas 3D hỏng thì khách phải thấy chữ giải thích, không phải ô trắng và
 * cũng không phải lần crash thứ hai.
 *
 * Vì sao cần test hành vi thật: bản sửa đầu tiên đặt boundary React **bên
 * trong** `<Canvas>`. R3F render children bằng reconciler Three.js, nên khi
 * fallback trả về `<div>`/`<p>` thì reconciler coi đó là phần tử THREE không
 * tồn tại và ném lỗi lần nữa. Script `scripts/test-glb-fallback.cjs` khi đó chỉ
 * so regex trên source nên vẫn báo PASS — đúng kiểu "test xanh, lỗi thật".
 *
 * Ở đây cắt đúng đường hỏng của môi trường thật, trên trang Studio vì đó là
 * trang render Canvas ở phía trình duyệt:
 *   1. `HTMLCanvasElement.getContext('webgl')` trả `null` (máy không có WebGL).
 *   2. File `.glb` trả 404 (asset lỗi/đổi tên) — phải rơi về bánh vẽ bằng code.
 *
 * Giới hạn đã biết: viewer 3D ở trang chi tiết sản phẩm nằm trong server
 * component, dữ liệu lấy bằng `fetch` phía Next server, nên `page.route` của
 * trình duyệt không chặn được đường đó. Nhánh viewer chỉ được kiểm bằng
 * `scripts/test-glb-fallback.cjs` (cấu trúc) — xem báo cáo, không coi là đã
 * kiểm hành vi.
 */

/**
 * Chỉ miễn trừ lỗi MÔI TRƯỜNG đã biết, không miễn trừ theo từ khoá chung.
 *
 * Trước đây allowlist là `/net::ERR|Failed to fetch|WebGL|context/i`. Hai chữ
 * "WebGL" và "context" quá rộng: chúng nuốt mọi lỗi ứng dụng tình cờ nhắc tới
 * hai từ đó (ví dụ "Cannot read properties of undefined (reading 'context')" —
 * đúng kiểu lỗi đã từng bị che trong `cake-builder.spec.ts`). Nay chỉ chấp nhận
 * thông báo cụ thể của three.js khi trình duyệt không cấp được WebGL, và lỗi
 * mạng của chính request bị chặn.
 */
const JS_ERROR_ALLOWLIST =
  /net::ERR|Failed to fetch|Error creating WebGL context|WebGL context (lost|was lost)/i;

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

test("mất WebGL: hiện thông báo thay vì canvas chết", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function patched(
      this: HTMLCanvasElement,
      contextId: string,
      ...rest: unknown[]
    ) {
      if (
        contextId === "webgl" ||
        contextId === "webgl2" ||
        contextId === "experimental-webgl"
      ) {
        return null;
      }
      return (original as unknown as (...args: unknown[]) => unknown).call(
        this,
        contextId,
        ...rest,
      );
    } as typeof HTMLCanvasElement.prototype.getContext;
  });

  await page.goto("/cake-builder");

  // Thông báo của boundary DOM nằm NGOÀI Canvas — chỉ hiện được nếu boundary
  // thật sự bắt lỗi tạo context, đúng thứ bản sửa trong Canvas không làm được.
  await expect(
    page.getByText("Không hiển thị được mô hình 3D", { exact: false }).first(),
  ).toBeVisible({ timeout: 30_000 });

  const real = errors.filter((m) => !JS_ERROR_ALLOWLIST.test(m));
  expect(real, "Lỗi JS khi mất WebGL: " + real.join(" | ")).toEqual([]);
});

test("GLB 404: vẫn có bánh dự phòng, không lỗi JS", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.route("**/*.glb", (route) => route.fulfill({ status: 404, body: "" }));

  await page.goto("/cake-builder");

  // Trang vẫn dùng được: giá hiển thị, bánh vẽ bằng code thay cho GLB hỏng.
  await expect(
    page.locator("text=/\\d{1,3}(\\.\\d{3})+\\s*₫/").first(),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("[data-cake3d] canvas")).toHaveCount(1);

  const real = errors.filter((m) => !JS_ERROR_ALLOWLIST.test(m));
  expect(real, "Lỗi JS khi GLB 404: " + real.join(" | ")).toEqual([]);
});

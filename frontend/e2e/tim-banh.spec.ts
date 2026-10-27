import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Trang tìm bánh bằng ảnh — kiểm ba thứ mà đề tài yêu cầu rõ:
 *
 *   1. Ảnh giả (không phải ảnh) phải bị chặn với thông báo đọc được.
 *   2. Ảnh quá dung lượng phải bị chặn trước khi gửi đi.
 *   3. Giao diện phải NÓI RÕ rằng % tương đồng không phải xác suất.
 *
 * Mọi request ra ngoài bị chặn bởi `isolateNetwork` — test này không đụng CSDL
 * thật, không nạp model CLIP, không tạo đơn.
 */

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

/** Tạo một file PNG hợp lệ trong bộ nhớ (không cần file thật trên đĩa). */
async function makePngBytes(): Promise<Buffer> {
  return Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
    "base64",
  );
}

test("từ chối file không phải ảnh", async ({ page }) => {
  await page.goto("/tim-banh");

  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Chọn ảnh từ máy" }).click();
  const fc = await chooser;

  await fc.setFiles({
    name: "khong-phai-anh.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("đây không phải ảnh"),
  });

  await expect(page.locator('[role="alert"]').first()).toContainText(
    "Chỉ hỗ trợ ảnh",
  );
});

test("từ chối ảnh quá 10 MB trước khi gửi đi", async ({ page }) => {
  await page.goto("/tim-banh");

  // Đếm số request tới API tìm kiếm — phải bằng 0 vì ảnh bị chặn ở client.
  let searchCalls = 0;
  await page.route("**/api/v1/search/by-image", (route) => {
    searchCalls++;
    return route.fulfill({ status: 200, body: JSON.stringify({ results: [], count: 0 }) });
  });

  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Chọn ảnh từ máy" }).click();
  const fc = await chooser;

  // File >10 MB: tạo buffer rác cỡ 11 MB. Client chặn theo KÍCH THƯỚC FILE
  // nên không cần nội dung là ảnh thật.
  await fc.setFiles({
    name: "lon.jpg",
    mimeType: "image/jpeg",
    buffer: Buffer.alloc(11 * 1024 * 1024, 0),
  });

  await expect(page.locator('[role="alert"]').first()).toContainText(
    "quá lớn",
  );
  expect(searchCalls).toBe(0);
});

test("giải thích rõ % tương đồng không phải xác suất", async ({ page }) => {
  await page.goto("/tim-banh");

  // Trả về một kết quả để giao diện hiện phần kết quả.
  await page.route("**/api/v1/search/by-image", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        count: 1,
        model: "ViT-B-32",
        timing_ms: { embed: 120, search: 40, total: 160 },
        results: [
          {
            product_id: "33333333-3333-3333-3333-333333333333",
            name: "Bánh kem tròn 1 tầng",
            image_url: "https://example.test/a.jpg",
            category: "sinh nhat",
            product_type: "cake",
            base_price: 350000,
            similarity: 0.82,
            similarity_percent: 82,
            three_d_model: null,
          },
        ],
      }),
    }),
  );

  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Chọn ảnh từ máy" }).click();
  const fc = await chooser;
  await fc.setFiles({
    name: "anh.jpg",
    mimeType: "image/jpeg",
    buffer: await makePngBytes(),
  });

  await page.getByRole("button", { name: "Tìm bánh giống nhất" }).click();

  await expect(page.getByText("1 mẫu bánh giống nhất")).toBeVisible();

  // Dòng giải thích phải nói rõ đây KHÔNG phải xác suất.
  const note = page.getByText(/không phải xác suất/i);
  await expect(note).toBeVisible();
});

test("chế độ chỉ mẫu có 3D gửi tham số lọc xuống API", async ({ page }) => {
  await page.goto("/tim-banh");

  let sentForm: string | null = null;
  await page.route("**/api/v1/search/by-image", (route) => {
    sentForm = route.request().postData() ?? "";
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        count: 0,
        model: "ViT-B-32",
        timing_ms: { embed: 100, search: 30, total: 130 },
        results: [],
      }),
    });
  });

  const chooser = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: "Chọn ảnh từ máy" }).click();
  const fc = await chooser;
  await fc.setFiles({
    name: "anh.jpg",
    mimeType: "image/jpeg",
    buffer: await makePngBytes(),
  });

  // Bật chế độ "Chỉ mẫu có 3D" rồi tìm.
  await page.getByRole("radio", { name: "Chỉ mẫu có 3D" }).click();
  await page.getByRole("button", { name: "Tìm bánh giống nhất" }).click();

  await expect(page.getByText("Không tìm thấy mẫu bánh phù hợp")).toBeVisible();
  expect(sentForm).toContain("has_3d_model");
  expect(sentForm).toContain("true");
});

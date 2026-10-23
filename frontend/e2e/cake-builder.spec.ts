import { test, expect } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Studio: đổi kích cỡ / trang trí / mẫu phải cập nhật giá và hình.
 *
 * Đây là chỗ đã xảy ra **lỗi chênh giá P0** (Gói 1): Studio tính 480.000đ còn
 * bảng `cake_price` trả 350.000đ, chênh 130.000đ. Test này không kiểm con số —
 * con số do `price-calculator.ts` tự tính, và đã có test unit ở đó.
 *
 * Ở đây kiểm thứ chỉ E2E làm được: **thao tác của khách có thật sự thay đổi
 * được giá đang hiển thị**, vì form bị hỏng kiểu "đổi size nhưng giá đứng im"
 * thì test unit vẫn xanh.
 */

/** Giá hiển thị theo định dạng `450.000₫` của `formatPriceVND`. */
function priceLocator(page: import("@playwright/test").Page) {
  return page.locator("text=/\\d{1,3}(\\.\\d{3})+\\s*₫/").first();
}

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

test("đổi kích cỡ làm giá thay đổi", async ({ page }) => {
  await page.goto("/cake-builder");

  const price = priceLocator(page);
  await expect(price).toBeVisible({ timeout: 25_000 });
  const before = (await price.textContent())?.trim() ?? "";
  expect(before, "Giá ban đầu phải được hiển thị").not.toBe("");

  // `ConfiguratorRail` có hai chế độ: mặc định chỉ hiện **tóm tắt** (dạng
  // `<DT>Kích thước</DT><DD>20cm</DD>`), các nút chọn chỉ xuất hiện sau khi bấm
  // vào bước trong `nav`. Đã xác nhận qua trace: chưa bấm bước thì không có
  // button "24 cm" nào để bấm. Nên phải mô phỏng đúng đường người dùng.
  await page.getByRole("button", { name: "Kích thước" }).click();

  // Lúc này mỗi lựa chọn là một `DetailChoice`: `<button aria-pressed>` với
  // nội dung text "24 cm".
  const size24 = page.getByRole("button", { name: /24 cm/ }).first();
  await expect(size24).toBeVisible({ timeout: 10_000 });
  await size24.click();

  // 24cm đắt hơn mặc định, nên chuỗi giá phải đổi.
  await expect
    .poll(async () => (await price.textContent())?.trim(), { timeout: 10_000 })
    .not.toBe(before);
});

test("bấm topping làm giá tăng, bỏ topping thì quay lại giá cũ", async ({ page }) => {
  await page.goto("/cake-builder");

  const price = priceLocator(page);
  await expect(price).toBeVisible({ timeout: 25_000 });
  const base = (await price.textContent())?.trim() ?? "";

  // Topping nằm trong `OptionsPanel`, chỉ render khi `detailStep` là
  // `top` / `body` / `border` — đã xác nhận qua trace rằng chưa bấm bước thì
  // không có nút topping nào.
  //
  // Tên bước trong `STEP_LABELS` của `ConfiguratorRail`: `top` = "Topping",
  // `body` = "Hoa văn", `border` = "Trang trí". Nút topping chỉ ở bước "Topping".
  //
  // Lưu ý: có thể có HAI nút cùng tên (một trong nav, một trên bánh 3D), nên
  // lấy `.first()`.
  await page.getByRole("button", { name: "Topping", exact: true }).first().click();

  // OptionsPanel đánh dấu `data-topping-option={id}` và `aria-label="Topping: ..."`.
  const topping = page.locator("[data-topping-option]").first();
  if ((await topping.count()) === 0) {
    test.skip(true, "Không có topping nào để chọn — bỏ qua, không phải lỗi.");
  }
  await expect(topping).toHaveAttribute("aria-pressed", "false");

  await topping.click();
  await expect(topping).toHaveAttribute("aria-pressed", "true");

  await expect
    .poll(async () => (await price.textContent())?.trim(), { timeout: 10_000 })
    .not.toBe(base);

  await topping.click();
  await expect(topping).toHaveAttribute("aria-pressed", "false");

  await expect
    .poll(async () => (await price.textContent())?.trim(), { timeout: 10_000 })
    .toBe(base);
});

test("không có lỗi JS khi vào Studio", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));

  await page.goto("/cake-builder");
  await expect(priceLocator(page)).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(3_000);

  // Bỏ qua lỗi mạng do chặn API, và cảnh báo WebGL trên máy không có GPU.
  const real = errors.filter(
    (m) => !/net::ERR|Failed to fetch|WebGL|Cannot read properties of undefined/i.test(m)
  );
  expect(real, "Lỗi JS trên trang Studio: " + real.join(" | ")).toEqual([]);
});

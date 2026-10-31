import { test, expect, type Page } from "@playwright/test";
import { isolateNetwork } from "../playwright.config";

/**
 * Modal xem trước: bàn phím phải dùng được.
 *
 * Trước đây chú thích ghi "trap focus" nhưng code chỉ nghe Escape và khoá cuộn
 * trang. Ba hệ quả đo được:
 *   1. Mở modal xong focus vẫn nằm ở nút phía sau — Tab đi vào nội dung bị che.
 *   2. Tab/Shift+Tab thoát ra khỏi modal, dù `aria-modal="true"`.
 *   3. Đóng modal thì mất dấu focus, người dùng bàn phím phải tab lại từ đầu.
 *
 * Ngoài ra hình xem trước dùng `CakeSVG` với `onZoneClick` rỗng, nên ba vùng
 * bánh vẫn là `role="button"` + `tabIndex=0` — tab vào ba nút không có tác dụng.
 */

async function openPreview(page: Page) {
  await page.goto("/cake-builder");

  // Nút "Xem trước & đặt bánh" chỉ mở sau khi đủ ba lựa chọn bắt buộc: hương vị,
  // loại kem, màu kem (`validateDesign`).
  //
  // Cấu trúc cần biết: `ConfiguratorRail` có hai chế độ. Ban đầu là danh sách
  // bước (`aria-label="Các bước cấu hình bánh"`). Bấm một bước thì aside đó BIẾN
  // MẤT và thay bằng panel chi tiết (`aria-label="Tùy chỉnh <bước>"`). Muốn sang
  // bước khác phải bấm "← Quay lại" trước — tab thẳng tới bước kế tiếp sẽ treo.
  const rail = page.getByLabel("Các bước cấu hình bánh");
  await expect(rail).toBeVisible({ timeout: 25_000 });

  await rail.getByRole("button", { name: /Hương vị/i }).first().click();
  const vanilla = page.getByRole("button", { name: "Vanilla", exact: true });
  await expect(vanilla).toBeVisible({ timeout: 10_000 });
  await vanilla.click();
  await expect(vanilla).toHaveAttribute("aria-pressed", "true");

  // "Loại kem" nằm cùng bước "Hương vị".
  const buttercream = page.getByRole("button", { name: "Buttercream", exact: true });
  await expect(buttercream).toBeVisible({ timeout: 10_000 });
  await buttercream.click();
  await expect(buttercream).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: /Quay lại/i }).click();
  await expect(rail).toBeVisible({ timeout: 10_000 });
  await rail.getByRole("button", { name: /Màu sắc/i }).first().click();

  const whiteCream = page.getByRole("button", { name: /Màu kem Trắng/i });
  await expect(whiteCream).toBeVisible({ timeout: 10_000 });
  await whiteCream.click();
  await expect(whiteCream).toHaveAttribute("aria-pressed", "true");

  const open = page.getByRole("button", { name: /Xem trước.*đặt bánh/i });
  await expect(open).toBeVisible({ timeout: 25_000 });
  await open.click();
  const dialog = page.getByRole("dialog", { name: "Xem trước thiết kế bánh" });
  await expect(dialog).toBeVisible({ timeout: 10_000 });
  return { dialog, open };
}

test.beforeEach(async ({ page }) => {
  await isolateNetwork(page);
});

// Mở modal phải đi qua ba bước cấu hình và render WebGL; đo trên máy này mất
// ~23 giây mỗi lần. Ngưỡng 30 giây mặc định chỉ còn vài giây cho phần kiểm tra
// bàn phím, nên test Tab hết giờ dù hành vi đúng. Đây là giới hạn tốc độ máy,
// không phải nới lỏng điều kiện kiểm tra.
test.setTimeout(180_000);

test("mở modal đưa focus vào trong, Tab không thoát ra ngoài", async ({ page }) => {
  const { dialog } = await openPreview(page);

  await expect
    .poll(() => dialog.evaluate((node) => node.contains(document.activeElement)))
    .toBe(true);

  // Tab nhiều lần: focus phải luôn nằm trong dialog, không nhảy ra trang nền.
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press("Tab");
    const inside = await dialog.evaluate((node) => node.contains(document.activeElement));
    expect(inside, `Tab lần ${i + 1} làm focus thoát khỏi modal`).toBe(true);
  }

  // Shift+Tab cũng phải ở lại trong.
  for (let i = 0; i < 6; i++) {
    await page.keyboard.press("Shift+Tab");
    const inside = await dialog.evaluate((node) => node.contains(document.activeElement));
    expect(inside, `Shift+Tab lần ${i + 1} làm focus thoát khỏi modal`).toBe(true);
  }
});

test("Shift+Tab từ khung modal không thoát ra trang nền", async ({ page }) => {
  const { dialog } = await openPreview(page);

  // Phải focus đúng `modalRef` — khung có `tabIndex={-1}`, KHÔNG phải div
  // `role="dialog"` bên ngoài. Focus vào div ngoài không làm gì (không
  // focusable), và khi đó phép thử vô nghĩa: nó pass kể cả khi đã gỡ phần xử
  // lý. Đã đo: mutation gỡ `outside` khỏi nhánh Shift+Tab vẫn cho test xanh
  // khi focus nhầm phần tử.
  const container = dialog.locator('[tabindex="-1"]').first();
  await container.evaluate((node) => (node as HTMLElement).focus());
  await expect
    .poll(() => container.evaluate((node) => node === document.activeElement))
    .toBe(true);

  await page.keyboard.press("Shift+Tab");
  const stillInside = await dialog.evaluate((node) =>
    node.contains(document.activeElement),
  );
  expect(
    stillInside,
    "Shift+Tab từ khung modal làm focus thoát ra trang nền",
  ).toBe(true);
});

test("Escape đóng modal và trả focus về nút đã mở nó", async ({ page }) => {
  const { dialog, open } = await openPreview(page);

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();

  // Focus phải quay lại nút mở modal, không phải về đầu trang.
  await expect(open).toBeFocused();
});

test("hình xem trước không có vùng bấm rỗng", async ({ page }) => {
  const { dialog } = await openPreview(page);

  // Ảnh xem trước chỉ để xem: không được có role=button nào bên trong.
  await expect(dialog.getByRole("button", { name: /zone/i })).toHaveCount(0);

  const focusableInPreview = await dialog
    .locator("svg [tabindex='0']")
    .count();
  expect(
    focusableInPreview,
    "hình xem trước còn vùng bấm rỗng khiến người dùng bàn phím tab vào nút vô tác dụng",
  ).toBe(0);
});

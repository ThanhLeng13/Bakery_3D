"use client";

/**
 * Ô đăng ký nhận tin ở footer.
 *
 * Tách thành client component riêng vì trang chủ là server component và
 * không thể truyền onSubmit từ đó xuống.
 *
 * Form CHƯA nối API. Chặn submit để không đẩy dữ liệu đi đâu cả và không
 * tải lại trang; khi nào có endpoint thật thì thay phần thân handleSubmit.
 */
export default function NewsletterForm() {
  return (
    <form
      className="flex gap-2"
      onSubmit={(e) => {
        e.preventDefault();
      }}
    >
      <label htmlFor="newsletter-email" className="sr-only">
        Email của bạn
      </label>
      <input
        id="newsletter-email"
        type="email"
        placeholder="Email của bạn..."
        className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3.5 py-2.5 text-[0.8125rem] text-ink placeholder:text-muted focus:border-ink focus:outline-none"
      />
      <button
        type="submit"
        className="rounded-lg bg-action px-4 py-2.5 text-[0.6875rem] font-medium uppercase tracking-[0.06em] text-surface transition-colors hover:bg-cocoa"
      >
        Gửi
      </button>
    </form>
  );
}

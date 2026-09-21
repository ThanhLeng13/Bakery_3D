"use client";

/**
 * Ô đăng ký nhận tin ở footer.
 *
 * Tách thành client component riêng vì trang chủ là server component và
 * không thể truyền onSubmit từ đó xuống.
 *
 * CHƯA có endpoint đăng ký. Trước đây form vẫn cho bấm "Gửi" rồi âm thầm vứt
 * dữ liệu đi — trông y như đã đăng ký thành công, mà thực tế không có gì xảy
 * ra. Nay input và nút đều bị vô hiệu hóa kèm dòng chú thích, để trạng thái
 * hiển thị đúng sự thật.
 *
 * Khi có endpoint thật: bỏ `disabled`, thêm state loading/error, và gọi API
 * trong handleSubmit.
 */
export default function NewsletterForm() {
  return (
    <div>
      <form className="flex gap-2">
        <label htmlFor="newsletter-email" className="sr-only">
          Email của bạn
        </label>
        <input
          id="newsletter-email"
          type="email"
          placeholder="Email của bạn..."
          disabled
          aria-describedby="newsletter-note"
          className="min-w-0 flex-1 rounded-lg border border-line bg-subtle px-3.5 py-2.5 text-[0.8125rem] text-ink placeholder:text-muted disabled:cursor-not-allowed disabled:opacity-70"
        />
        <button
          type="button"
          disabled
          aria-describedby="newsletter-note"
          className="rounded-lg bg-action px-4 py-2.5 text-[0.6875rem] font-medium uppercase tracking-[0.06em] text-surface disabled:cursor-not-allowed disabled:opacity-50"
        >
          Gửi
        </button>
      </form>
      <p id="newsletter-note" className="mt-2 text-[0.75rem] leading-snug text-muted">
        Chức năng đang được hoàn thiện.
      </p>
    </div>
  );
}

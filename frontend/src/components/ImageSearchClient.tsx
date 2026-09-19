"use client";

/**
 * Tìm kiếm bánh bằng hình ảnh (CLIP) — trụ cột 2 của đề tài.
 *
 * Luồng: khách chọn/kéo ảnh → gửi lên API → CLIP sinh vector → so sánh với kho
 * → hiển thị kết quả kèm % tương đồng.
 *
 * Quyết định thiết kế:
 *   - Xem trước ảnh bằng createObjectURL và THU HỒI URL khi đổi ảnh/unmount.
 *     Không thu hồi sẽ rò rỉ bộ nhớ sau vài lần chọn ảnh.
 *   - Kiểm tra loại file và dung lượng ở client trước khi gửi, để khách nhận
 *     phản hồi tức thì thay vì chờ upload xong mới báo lỗi.
 *   - Dùng AbortController: khách đổi ảnh giữa chừng thì hủy request cũ, tránh
 *     kết quả của ảnh cũ ghi đè kết quả ảnh mới.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Giới hạn phía server là 10 MB; chặn sớm ở client cho phản hồi nhanh. */
const MAX_FILE_BYTES = 10 * 1024 * 1024;

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];

interface SearchResult {
  product_id: string;
  name: string;
  image_url: string;
  category: string | null;
  product_type: string | null;
  base_price: number | null;
  similarity: number;
  similarity_percent: number;
}

interface SearchResponse {
  results: SearchResult[];
  count: number;
  timing_ms: { embed: number; search: number; total: number };
  model: string;
}

function formatPrice(price: number | null): string {
  if (price === null || price === undefined) return "Liên hệ";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(price);
}

/**
 * Icon "khung ảnh có núi" — dùng chung cho vùng kéo thả và ô ảnh lỗi.
 *
 * Vẽ bằng SVG nét mảnh thay vì emoji: emoji render khác nhau trên mỗi hệ điều
 * hành và lệch tông xám trung tính của thương hiệu.
 */
function ImagePlaceholderIcon({ className }: { className: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="6" y="10" width="36" height="28" rx="3" />
      <circle cx="17" cy="20" r="3.5" />
      <path d="M6 32l10-9 8 7 6-5 12 11" />
    </svg>
  );
}

export default function ImageSearchClient() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [timing, setTiming] = useState<SearchResponse["timing_ms"] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [imgErrors, setImgErrors] = useState<Record<string, boolean>>({});

  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Thu hồi object URL khi ảnh đổi hoặc component unmount — tránh rò rỉ bộ nhớ.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  // Hủy request đang bay nếu component bị unmount giữa chừng.
  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const pickFile = useCallback(
    (next: File | null) => {
      setError("");
      setResults(null);
      setTiming(null);

      // Giải phóng URL cũ trước khi tạo URL mới.
      if (previewUrl) URL.revokeObjectURL(previewUrl);

      if (!next) {
        setFile(null);
        setPreviewUrl(null);
        return;
      }

      if (!ACCEPTED_TYPES.includes(next.type)) {
        setFile(null);
        setPreviewUrl(null);
        setError("Chỉ hỗ trợ ảnh JPG, PNG, WEBP hoặc GIF.");
        return;
      }

      if (next.size > MAX_FILE_BYTES) {
        setFile(null);
        setPreviewUrl(null);
        setError("Ảnh quá lớn. Vui lòng chọn ảnh dưới 10 MB.");
        return;
      }

      setFile(next);
      setPreviewUrl(URL.createObjectURL(next));
    },
    [previewUrl],
  );

  async function handleSearch() {
    if (!file) return;

    // Hủy request cũ nếu khách bấm tìm nhiều lần.
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("match_count", "6");

      const response = await fetch(`${API_BASE_URL}/api/v1/search/by-image`, {
        method: "POST",
        body: form,
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(
          body?.detail || "Không thể tìm kiếm. Vui lòng thử lại.",
        );
      }

      const data: SearchResponse = await response.json();
      setResults(data.results);
      setTiming(data.timing_ms);
    } catch (err) {
      // Bỏ qua lỗi do chính mình hủy request.
      if (err instanceof DOMException && err.name === "AbortError") return;
      setError(
        err instanceof Error ? err.message : "Không thể tìm kiếm. Vui lòng thử lại.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    const dropped = event.dataTransfer.files?.[0];
    if (dropped) pickFile(dropped);
  }

  return (
    <main className="min-h-screen bg-surface">
      <div className="page-container py-10 sm:py-14">
        {/* Tiêu đề */}
        <header className="text-center mb-10">
          <h1 className="font-heading text-3xl sm:text-4xl font-bold text-ink mb-3">
            Tìm bánh bằng hình ảnh
          </h1>
          <p className="text-muted text-base sm:text-lg max-w-[640px] mx-auto">
            Tải lên ảnh chiếc bánh bạn yêu thích, chúng tôi sẽ tìm những mẫu bánh
            giống nhất trong tiệm.
          </p>
        </header>

        <div className="max-w-[720px] mx-auto">
          {/* Vùng chọn ảnh */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            className={`rounded-2xl border-2 border-dashed bg-white p-8 text-center transition-colors ${
              dragging ? "border-action bg-subtle" : "border-line"
            }`}
          >
            {previewUrl ? (
              <div className="flex flex-col items-center gap-4">
                <div className="relative h-56 w-56 rounded-2xl overflow-hidden bg-subtle">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={previewUrl}
                    alt="Ảnh bạn đã chọn"
                    className="h-full w-full object-cover"
                  />
                </div>
                <p className="text-sm text-muted">
                  {file?.name} · {((file?.size ?? 0) / 1024).toFixed(0)} KB
                </p>
                <div className="flex flex-wrap gap-3 justify-center">
                  <button
                    type="button"
                    onClick={handleSearch}
                    disabled={loading}
                    className="btn btn-primary disabled:opacity-60"
                  >
                    {loading ? "Đang tìm..." : "Tìm bánh giống nhất"}
                  </button>
                  <button
                    type="button"
                    onClick={() => pickFile(null)}
                    disabled={loading}
                    className="btn btn-secondary disabled:opacity-60"
                  >
                    Chọn ảnh khác
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-5">
                {/* Icon nét mảnh thay cho emoji: ăn khớp tông xám trung tính
                    của thương hiệu, và không phụ thuộc font emoji của hệ điều
                    hành (mỗi máy render một kiểu). */}
                <ImagePlaceholderIcon className="h-14 w-14 text-brand" />
                <p className="text-ink text-lg font-medium">
                  Kéo ảnh bánh vào đây, hoặc
                </p>
                <button
                  type="button"
                  onClick={() => inputRef.current?.click()}
                  className="btn btn-primary"
                >
                  Chọn ảnh từ máy
                </button>
                <p className="text-sm text-muted">
                  Hỗ trợ JPG, PNG, WEBP, GIF · tối đa 10 MB
                </p>
              </div>
            )}

            <input
              ref={inputRef}
              type="file"
              accept={ACCEPTED_TYPES.join(",")}
              className="hidden"
              onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
            />
          </div>

          {/* Lỗi */}
          {error && (
            <div
              role="alert"
              className="mt-6 rounded-2xl border border-line bg-white px-5 py-4 text-sm text-ink"
            >
              {error}
            </div>
          )}

          {/* Đang tải */}
          {loading && (
            <div className="mt-8 text-center" aria-live="polite">
              <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-line border-t-action" />
              <p className="mt-3 text-sm text-muted">
                Đang phân tích hình ảnh và tìm trong kho bánh...
              </p>
            </div>
          )}

          {/* Kết quả */}
          {results && (
            <section className="mt-10" aria-labelledby="ket-qua-heading">
              <div className="flex flex-wrap items-baseline justify-between gap-2 mb-5">
                <h2
                  id="ket-qua-heading"
                  className="font-heading text-xl sm:text-2xl font-bold text-ink"
                >
                  {results.length > 0
                    ? `${results.length} mẫu bánh giống nhất`
                    : "Không tìm thấy mẫu bánh phù hợp"}
                </h2>
                {timing && (
                  <p className="text-xs text-muted">
                    Phân tích {timing.embed.toFixed(0)} ms · Tìm kiếm{" "}
                    {timing.search.toFixed(0)} ms
                  </p>
                )}
              </div>

              {results.length === 0 ? (
                <p className="text-muted text-sm rounded-2xl border border-line bg-white px-5 py-4">
                  Chưa tìm được mẫu bánh nào giống ảnh của bạn. Bạn thử tải ảnh
                  chụp rõ hơn, hoặc xem toàn bộ menu bánh.
                </p>
              ) : (
                <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                  {results.map((item) => (
                    <li key={item.product_id + item.image_url}>
                      <Link
                        href={`/products/${item.product_id}`}
                        className="group block rounded-2xl bg-white border border-line shadow-sm hover:shadow-md hover:border-brand transition-all overflow-hidden h-full"
                      >
                        <div className="aspect-square relative bg-subtle overflow-hidden">
                          {item.image_url && !imgErrors[item.product_id] ? (
                            <Image
                              src={item.image_url}
                              alt={item.name}
                              fill
                              sizes="(max-width: 640px) 50vw, 33vw"
                              className="object-cover group-hover:scale-105 transition-transform duration-300"
                              onError={() =>
                                setImgErrors((prev) => ({
                                  ...prev,
                                  [item.product_id]: true,
                                }))
                              }
                            />
                          ) : (
                            <div className="flex h-full items-center justify-center">
                              <ImagePlaceholderIcon className="h-10 w-10 text-brand" />
                            </div>
                          )}
                          {/* % tương đồng — thông tin chính khách cần thấy.
                              Nền đặc thay vì mờ 85% để chữ luôn đạt tương phản
                              AA trên mọi loại ảnh nền. */}
                          <span className="absolute top-2 right-2 rounded-full bg-ink px-3 py-1 text-sm font-semibold text-white">
                            {item.similarity_percent.toFixed(0)}%
                          </span>
                        </div>
                        <div className="p-3">
                          <h3 className="text-sm font-semibold text-ink line-clamp-2 leading-snug">
                            {item.name}
                          </h3>
                          <p className="mt-1 text-sm text-muted">
                            {formatPrice(item.base_price)}
                          </p>
                        </div>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      </div>
    </main>
  );
}

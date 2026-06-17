"use client";

import { useState, useCallback, useEffect } from "react";
import { flushSync } from "react-dom";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import StarRating from "./StarRating";
import { ProductDetailResponse, StockInfo, StockByBranchResponse, BranchStock } from "@/types";
import { apiClient } from "@/lib/api";
import { useCart } from "@/contexts/CartContext";
import { useAuthContext } from "@/contexts/AuthContext";

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(price);
}

/** Format a YYYY-MM-DD date string as DD/MM/YYYY without timezone conversion.
 * Using new Date(dateStr) treats the string as UTC midnight and calling
 * toLocaleDateString() shifts it to the previous day in timezones behind UTC.
 */
function formatDateOnly(dateStr: string): string {
  const [y, m, d] = dateStr.split("-");
  return `${d}/${m}/${y}`;
}

interface Review {
  id: string;
  rating: number;
  comment: string | null;
  customer_name: string;
  created_at: string;
}

interface ReviewsResponse {
  reviews: Review[];
  pagination: {
    page: number;
    total_pages: number;
    total_items: number;
    has_next: boolean;
    has_previous: boolean;
  };
  average_rating: number | null;
  review_count: number;
}


interface StarPickerProps {
  value: number;
  onChange: (v: number) => void;
}

function StarPicker({ value, onChange }: StarPickerProps) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1" role="group" aria-label="Chọn số sao đánh giá">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          aria-label={`${star} sao`}
          className="transition-transform hover:scale-110 focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-pastel rounded"
        >
          <svg
            className={`w-8 h-8 transition-colors ${
              (hovered || value) >= star ? "text-yellow-400" : "text-gray-200"
            }`}
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
          </svg>
        </button>
      ))}
    </div>
  );
}

const STAR_LABELS = ["", "Rất tệ", "Tệ", "Bình thường", "Tốt", "Xuất sắc"];



function ReviewSubmitForm({
  productId,
  onSuccess,
}: {
  productId: string;
  onSuccess: () => void;
}) {
  const { isAuthenticated } = useAuthContext();
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating === 0) { setError("Vui lòng chọn số sao."); return; }
    setSubmitting(true);
    setError(null);
    try {
      await apiClient.post("/api/v1/reviews", {
        product_id: productId,
        rating,
        comment: comment.trim() || null,
      });
      setSuccess(true);
      setShowForm(false);
      onSuccess();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string | { msg: string }[] };
      let errorMsg = "Không thể gửi đánh giá. Vui lòng thử lại.";
      if (typeof apiErr?.detail === "string") {
        errorMsg = apiErr.detail;
      } else if (Array.isArray(apiErr?.detail)) {
        errorMsg = apiErr.detail[0]?.msg || errorMsg;
      }
      setError(errorMsg);
    } finally {
      setSubmitting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="bg-gradient-to-br from-pink-pastel/5 to-amber-50 rounded-2xl p-5 border border-pink-pastel/20 text-center">
        <p className="text-mocha/70 text-sm mb-3">
          Đăng nhập để chia sẻ cảm nhận của bạn về sản phẩm này!
        </p>
        <Link
          href="/auth/login"
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-pink-pastel text-white text-sm font-medium rounded-full hover:bg-pink-pastel/90 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
          </svg>
          Đăng nhập ngay
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-2xl p-5 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <div>
          <p className="font-medium text-green-800 text-sm">Cảm ơn bạn đã đánh giá! 🎉</p>
          <p className="text-green-700 text-xs mt-0.5">Đánh giá của bạn đã được ghi nhận thành công.</p>
        </div>
      </div>
    );
  }

  if (!showForm) {
    return (
      <button
        onClick={() => setShowForm(true)}
        className="w-full flex items-center justify-center gap-2 py-3 px-5 rounded-2xl border-2 border-dashed border-pink-pastel/30 text-pink-pastel hover:bg-pink-pastel/5 hover:border-pink-pastel/50 transition-all text-sm font-medium group"
      >
        <svg className="w-5 h-5 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
        </svg>
        Viết đánh giá của bạn
      </button>
    );
  }

  return (
    <div className="bg-gradient-to-br from-white to-pink-pastel/5 rounded-2xl border border-pink-pastel/15 overflow-hidden shadow-sm">
      {/* Form header */}
      <div className="bg-gradient-to-r from-pink-pastel/10 to-amber-50/50 px-5 py-3 border-b border-pink-pastel/10 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">✍️</span>
          <span className="font-semibold text-mocha text-sm">Viết đánh giá</span>
        </div>
        <button
          onClick={() => setShowForm(false)}
          className="text-mocha/40 hover:text-mocha/70 transition-colors p-1 rounded-full"
          aria-label="Đóng form"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="p-5 space-y-4">
        {/* Star Picker */}
        <div>
          <label className="block text-xs font-semibold text-mocha/60 uppercase tracking-wide mb-2">
            Đánh giá của bạn <span className="text-red-400">*</span>
          </label>
          <div className="flex items-center gap-3">
            <StarPicker value={rating} onChange={setRating} />
            {rating > 0 && (
              <span className="text-sm font-medium text-yellow-600">
                {STAR_LABELS[rating]}
              </span>
            )}
          </div>
        </div>

        {/* Comment */}
        <div>
          <label htmlFor="review-comment" className="block text-xs font-semibold text-mocha/60 uppercase tracking-wide mb-2">
            Nhận xét <span className="text-mocha/30">(tuỳ chọn)</span>
          </label>
          <textarea
            id="review-comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={1000}
            rows={3}
            placeholder="Chia sẻ cảm nhận của bạn về sản phẩm này..."
            className="w-full px-3 py-2.5 rounded-xl border border-mocha/15 bg-white text-mocha text-sm resize-none focus:outline-none focus:ring-2 focus:ring-pink-pastel/40 focus:border-pink-pastel/50 placeholder:text-mocha/30"
          />
          <p className="text-xs text-mocha/30 text-right mt-1">{comment.length}/1000</p>
        </div>

        {/* Error */}
        {error && (
          <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-xl border border-red-200">
            {error}
          </p>
        )}

        {/* Submit */}
        <div className="flex gap-2 pt-1">
          <button
            type="button"
            onClick={() => setShowForm(false)}
            className="flex-1 py-2.5 px-4 text-sm font-medium text-mocha/70 border border-mocha/15 rounded-full hover:bg-mocha/5 transition-colors"
          >
            Huỷ
          </button>
          <button
            type="submit"
            disabled={submitting || rating === 0}
            className="flex-2 flex-grow py-2.5 px-5 text-sm font-semibold bg-pink-pastel text-white rounded-full hover:bg-pink-pastel/90 transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            {submitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Đang gửi...
              </span>
            ) : (
              "Gửi đánh giá"
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

function ReviewsSection({ productId }: { productId: string }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [reviewCount, setReviewCount] = useState(0);
  const [avgRating, setAvgRating] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchReviews = useCallback(async (pageNum: number) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: pageNum.toString(), page_size: "10" });
      const data = await apiClient.get<ReviewsResponse>(
        `/api/v1/products/${productId}/reviews?${params}`
      );
      setReviews(data.reviews);
      setTotalPages(data.pagination.total_pages);
      setReviewCount(data.review_count);
      setAvgRating(data.average_rating);
    } catch {
      // Silently fail - non-critical
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    fetchReviews(page);
  }, [fetchReviews, page]);

  // computeDistribution was removed

  return (
    <section className="pt-6 border-t border-mocha/10 space-y-5" aria-label="Đánh giá sản phẩm">
      {/* Section heading */}
      <div className="flex items-center justify-between">
        <h2 className="font-heading text-xl font-bold text-mocha">
          Đánh giá & Nhận xét
        </h2>
        <span className="text-sm text-mocha/50">{reviewCount} đánh giá</span>
      </div>

      {/* Rating summary card */}
      {(avgRating !== null || reviewCount > 0) && (
        <div className="bg-gradient-to-br from-amber-50/80 to-yellow-50/50 rounded-2xl p-4 border border-yellow-200/50 flex gap-4 items-start">
          {/* Big score */}
          <div className="flex-1 text-center flex flex-col items-center justify-center py-2">
            <p className="text-4xl font-bold text-mocha leading-none">
              {avgRating !== null ? avgRating.toFixed(1) : "—"}
            </p>
            <div className="flex justify-center mt-2 gap-1">
              {Array.from({ length: 5 }).map((_, i) => (
                <svg
                  key={i}
                  className={`w-4 h-4 ${i < Math.round(avgRating ?? 0) ? "text-yellow-400" : "text-gray-200"}`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>
            <p className="text-sm text-mocha/60 mt-2">{reviewCount} đánh giá</p>
          </div>
        </div>
      )}

      {/* Submit form */}
      <ReviewSubmitForm productId={productId} onSuccess={() => { setPage(1); fetchReviews(1); }} />

      {/* Reviews list */}
      {loading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-xl p-4 animate-pulse border border-mocha/5">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 rounded-full bg-mocha/10" />
                <div className="flex-1">
                  <div className="h-3 bg-mocha/10 rounded w-24 mb-1" />
                  <div className="h-2 bg-mocha/5 rounded w-16" />
                </div>
              </div>
              <div className="h-3 bg-mocha/5 rounded w-full mb-1" />
              <div className="h-3 bg-mocha/5 rounded w-3/4" />
            </div>
          ))}
        </div>
      )}

      {!loading && reviews.length === 0 && (
        <div className="text-center py-8">
          <p className="text-3xl mb-2">🍰</p>
          <p className="text-mocha/60 text-sm">
            Chưa có đánh giá nào. Hãy là người đầu tiên!
          </p>
        </div>
      )}

      {!loading && reviews.length > 0 && (
        <div className="space-y-3">
          {reviews.map((review) => {
            // Avatar initials
            const initials = review.customer_name
              .split(" ")
              .slice(-2)
              .map((w) => w[0])
              .join("")
              .toUpperCase();
            // Avatar color based on name hash
            const colors = [
              "bg-pink-200 text-pink-800",
              "bg-purple-200 text-purple-800",
              "bg-blue-200 text-blue-800",
              "bg-green-200 text-green-800",
              "bg-amber-200 text-amber-800",
              "bg-rose-200 text-rose-800",
            ];
            const colorIdx =
              review.customer_name
                .split("")
                .reduce((acc, c) => acc + c.charCodeAt(0), 0) % colors.length;

            return (
              <div key={review.id} className="bg-white rounded-2xl p-4 border border-mocha/5 hover:border-mocha/10 transition-colors">
                <div className="flex items-start gap-3">
                  {/* Avatar */}
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${colors[colorIdx]}`}>
                    {initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="font-semibold text-mocha text-sm truncate">
                        {review.customer_name}
                      </span>
                      <span className="text-xs text-mocha/40 flex-shrink-0">
                        {formatDateOnly(review.created_at.split("T")[0])}
                      </span>
                    </div>
                    {/* Stars */}
                    <div className="flex items-center gap-0.5 mt-0.5 mb-2">
                      {Array.from({ length: 5 }).map((_, i) => (
                        <svg
                          key={i}
                          className={`w-3.5 h-3.5 ${i < review.rating ? "text-yellow-400" : "text-gray-200"}`}
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                        </svg>
                      ))}
                      <span className="text-xs text-mocha/40 ml-1">{STAR_LABELS[review.rating]}</span>
                    </div>
                    {review.comment && (
                      <p className="text-sm text-mocha/80 leading-relaxed">{review.comment}</p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center gap-2 mt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-2 rounded-full text-sm bg-white text-mocha border border-mocha/10 hover:bg-pink-pastel/10 disabled:opacity-40 disabled:cursor-not-allowed min-h-[44px] min-w-[44px]"
              >
                ←
              </button>
              <span className="flex items-center text-sm text-mocha/60 px-2">
                {page}/{totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-2 rounded-full text-sm bg-white text-mocha border border-mocha/10 hover:bg-pink-pastel/10 disabled:opacity-40 disabled:cursor-not-allowed min-h-[44px] min-w-[44px]"
              >
                →
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

interface ProductDetailClientProps {
  product: ProductDetailResponse;
  stockInfo?: StockInfo | null; // only for sweet products
  stockByBranch?: StockByBranchResponse | null; // pre-fetched (optional fallback)
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ProductDetailClient({ product, stockInfo, stockByBranch: initialStockByBranch }: ProductDetailClientProps) {
  const router = useRouter();
  const { addItem, openCart } = useCart();
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [selectedSize, setSelectedSize] = useState<string | null>(
    product.sizes.length > 0 ? product.sizes[0].name : null
  );
  const [selectedFlavor, setSelectedFlavor] = useState<string | null>(
    product.flavors.length > 0 ? product.flavors[0].name : null
  );
  const [imgErrors, setImgErrors] = useState<Set<number>>(new Set());
  const [addedToCart, setAddedToCart] = useState(false);

  // Client-side fetch for branch stock (more reliable than SSR prop)
  const isCake = product.product_type === "cake";
  const isSweet = !isCake;

  const [stockByBranch, setStockByBranch] = useState<StockByBranchResponse | null>(
    initialStockByBranch ?? null
  );
  const [branchLoading, setBranchLoading] = useState(isSweet && !initialStockByBranch);

  useEffect(() => {
    if (!isSweet) return;
    // active flag: if the effect re-runs (product.id changed) the cleanup sets
    // active=false so any in-flight response for the previous product is ignored
    let active = true;
    // Reset stale state from previous product BEFORE fetching new data
    setSelectedBranch(null);
    setStockByBranch(null);
    // Always fetch fresh data on the client
    setBranchLoading(true);
    fetch(`${API_BASE}/api/v1/products/${product.id}/stock-by-branch`, {
      cache: "no-store",
    })
      .then((res) => res.ok ? res.json() : null)
      .then((data: StockByBranchResponse | null) => {
        if (active && data) setStockByBranch(data);
      })
      .catch(() => {})
      .finally(() => { if (active) setBranchLoading(false); });
    return () => { active = false; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product.id]);

  // All branches (including out-of-stock) for display
  const allBranches: BranchStock[] = stockByBranch?.branches ?? [];

  // Auto-select: first branch with stock, else first branch overall
  const [selectedBranch, setSelectedBranch] = useState<BranchStock | null>(null);

  // Update selected branch when data arrives
  useEffect(() => {
    if (allBranches.length > 0 && selectedBranch === null) {
      const first = allBranches.find((b) => b.quantity_available > 0) ?? allBranches[0];
      setSelectedBranch(first);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stockByBranch]);

  // Out-of-stock: selected branch has 0 stock (or no branches at all)
  const selectedBranchStock = selectedBranch?.quantity_available ?? 0;
  const isOutOfStock = isSweet && (
    allBranches.length === 0
      ? (stockInfo != null && (stockInfo?.total_available ?? 0) === 0)
      : selectedBranchStock === 0
  );

  // Low stock warning for selected branch
  const isLowStock = isSweet && !isOutOfStock && selectedBranchStock > 0 && selectedBranchStock <= 5;

  const handleImageError = (index: number) => {
    setImgErrors((prev) => new Set(prev).add(index));
  };

  const getSelectedSizePrice = (): number => {
    if (!selectedSize) return product.base_price;
    const size = product.sizes.find((s) => s.name === selectedSize);
    return size?.price ?? product.base_price;
  };

  const getSelectedFlavorCost = (): number => {
    if (!selectedFlavor) return 0;
    const flavor = product.flavors.find((f) => f.name === selectedFlavor);
    return flavor?.additional_cost ?? 0;
  };

  const totalPrice = isSweet
    ? product.base_price
    : getSelectedSizePrice() + getSelectedFlavorCost();

  const handleAddToCart = () => {
    if (isOutOfStock) return;
    addItem({
      productId: product.id,
      productName: product.name,
      imageUrl: product.images.length > 0 ? product.images[0].url : null,
      unitPrice: product.base_price,
      expiresAt: selectedBranch?.expires_soonest ?? stockInfo?.expires_soonest ?? null,
      branchId: selectedBranch?.branch_id ?? null,
      branchName: selectedBranch?.branch_name ?? null,
    });
    setAddedToCart(true);
    setTimeout(() => setAddedToCart(false), 2500);
  };

  const handleBuyNow = () => {
    if (isOutOfStock) return;
    // flushSync forces React to immediately commit the addItem state update
    // so the in-memory cart (read by useCart()/checkout page) is populated
    // BEFORE router.push navigates. localStorage persistence of bakery_cart
    // still happens asynchronously via CartProvider's useEffect.
    flushSync(() => {
      addItem({
        productId: product.id,
        productName: product.name,
        imageUrl: product.images.length > 0 ? product.images[0].url : null,
        unitPrice: product.base_price,
        expiresAt: selectedBranch?.expires_soonest ?? stockInfo?.expires_soonest ?? null,
        branchId: selectedBranch?.branch_id ?? null,
        branchName: selectedBranch?.branch_name ?? null,
      });
    });
    router.push("/checkout");
  };

  const mainImage =
    product.images.length > 0 && !imgErrors.has(selectedImageIndex)
      ? product.images[selectedImageIndex]
      : null;

  return (
    <main className="min-h-screen bg-cream">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Breadcrumb */}
        <nav className="mb-6" aria-label="Breadcrumb">
          <ol className="flex items-center gap-2 text-sm text-mocha/60">
            <li>
              <Link href="/products" className="hover:text-pink-pastel transition-colors">
                Danh mục
              </Link>
            </li>
            <li aria-hidden="true">/</li>
            <li className="text-mocha font-medium truncate">{product.name}</li>
          </ol>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
          {/* Image Gallery */}
          <section aria-label="Hình ảnh sản phẩm">
            {/* Main Image */}
            <div className="aspect-square rounded-2xl overflow-hidden bg-gray-100 relative">
              {mainImage ? (
                <Image
                  src={mainImage.url}
                  alt={product.name}
                  fill
                  sizes="(max-width: 1024px) 100vw, 50vw"
                  className="object-cover"
                  onError={() => handleImageError(selectedImageIndex)}
                  priority
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-cream">
                  <svg
                    className="w-24 h-24 text-mocha/20"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M12 8c-2.21 0-4 1.79-4 4h8c0-2.21-1.79-4-4-4zM5 12h14v2a4 4 0 01-4 4H9a4 4 0 01-4-4v-2zM9 8V6a3 3 0 016 0v2"
                    />
                  </svg>
                </div>
              )}
            </div>

            {/* Thumbnails */}
            {product.images.length > 1 && (
              <div className="flex gap-2 mt-4 overflow-x-auto pb-2">
                {product.images.map((image, index) => (
                  <button
                    key={image.id}
                    onClick={() => setSelectedImageIndex(index)}
                    className={`flex-shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden border-2 transition-colors min-w-[44px] min-h-[44px] relative ${
                      selectedImageIndex === index
                        ? "border-pink-pastel"
                        : "border-transparent hover:border-mocha/20"
                    }`}
                    aria-label={`Xem hình ${index + 1}`}
                    aria-current={selectedImageIndex === index ? "true" : undefined}
                  >
                    {!imgErrors.has(index) ? (
                      <Image
                        src={image.url}
                        alt=""
                        fill
                        sizes="80px"
                        className="object-cover"
                        onError={() => handleImageError(index)}
                      />
                    ) : (
                      <div className="w-full h-full bg-gray-200 flex items-center justify-center">
                        <svg
                          className="w-6 h-6 text-mocha/20"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                          aria-hidden="true"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14"
                          />
                        </svg>
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Product Info */}
          <section aria-label="Thông tin sản phẩm" className="space-y-6">
            {/* Name & Category */}
            <div>
              <span className="inline-block px-3 py-1 text-xs font-medium bg-pink-pastel/10 text-pink-pastel rounded-full mb-2">
                {product.category}
              </span>
              <h1 className="font-heading text-2xl sm:text-3xl font-bold text-mocha">
                {product.name}
              </h1>
            </div>

            {/* Rating */}
            <StarRating
              rating={product.average_rating}
              reviewCount={product.review_count}
              size="md"
            />

            {/* Description */}
            {product.description && (
              <p className="text-mocha/80 leading-relaxed">{product.description}</p>
            )}

            {/* Size Selector */}
            {product.sizes.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-mocha mb-3">Kích thước</h2>
                <div className="flex flex-wrap gap-2">
                  {product.sizes.map((size) => (
                    <button
                      key={size.name}
                      onClick={() => setSelectedSize(size.name)}
                      className={`px-4 py-2 rounded-full text-sm font-medium min-h-[44px] transition-colors ${
                        selectedSize === size.name
                          ? "bg-pink-pastel text-white shadow-sm"
                          : "bg-white text-mocha border border-mocha/10 hover:border-pink-pastel"
                      }`}
                    >
                      {size.name} — {formatPrice(size.price)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Flavor Options */}
            {product.flavors.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-mocha mb-3">Hương vị</h2>
                <div className="flex flex-wrap gap-2">
                  {product.flavors.map((flavor) => (
                    <button
                      key={flavor.name}
                      onClick={() => setSelectedFlavor(flavor.name)}
                      className={`px-4 py-2 rounded-full text-sm font-medium min-h-[44px] transition-colors ${
                        selectedFlavor === flavor.name
                          ? "bg-pink-pastel text-white shadow-sm"
                          : "bg-white text-mocha border border-mocha/10 hover:border-pink-pastel"
                      }`}
                    >
                      {flavor.name}
                      {flavor.additional_cost > 0 && ` (+${formatPrice(flavor.additional_cost)})`}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Branch Stock Section — sweet products */}
            {isSweet && (
              <div className="bg-white rounded-xl p-4 sm:p-5 border border-mocha/5">
                <h2 className="text-sm font-semibold text-mocha mb-3 flex items-center gap-2">
                  <svg className="w-4 h-4 text-pink-pastel" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Tồn kho theo chi nhánh
                </h2>

                {branchLoading ? (
                  /* Skeleton loading */
                  <div className="space-y-2 animate-pulse">
                    {[1, 2, 3].map((i) => (
                      <div key={i} className="h-14 bg-gray-100 rounded-xl" />
                    ))}
                  </div>
                ) : allBranches.length === 0 ? (
                  <p className="text-sm text-mocha/50 text-center py-3">Không có thông tin chi nhánh.</p>
                ) : (
                  <div className="space-y-2">
                    {allBranches.map((branch) => {
                      const isSelected = selectedBranch?.branch_id === branch.branch_id;
                      const isAvail = branch.quantity_available > 0;
                      const isLow = isAvail && branch.quantity_available <= 5;
                      return (
                        <button
                          key={branch.branch_id ?? "no-branch"}
                          onClick={() => isAvail && setSelectedBranch(branch)}
                          disabled={!isAvail}
                          className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border-2 transition-all text-left ${
                            !isAvail
                              ? "opacity-60 cursor-not-allowed bg-gray-50 border-gray-200"
                              : isSelected
                              ? "border-pink-pastel bg-pink-pastel/5 shadow-sm"
                              : "border-mocha/10 hover:border-pink-pastel/50 hover:bg-pink-pastel/5 bg-white"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            {/* Radio indicator */}
                            <div className={`w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center ${
                              isSelected ? "border-pink-pastel" : "border-mocha/30"
                            }`}>
                              {isSelected && (
                                <div className="w-2 h-2 rounded-full bg-pink-pastel" />
                              )}
                            </div>
                            <div>
                              <p className={`text-sm font-medium ${
                                isSelected ? "text-pink-pastel" : isAvail ? "text-mocha" : "text-mocha/50"
                              }`}>
                                {branch.branch_name}
                              </p>
                              {branch.branch_address && (
                                <p className="text-xs text-mocha/40 mt-0.5">{branch.branch_address}</p>
                              )}
                            </div>
                          </div>
                          {/* Stock badge */}
                          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full flex-shrink-0 ${
                            !isAvail
                              ? "bg-red-100 text-red-600"
                              : isLow
                              ? "bg-amber-100 text-amber-700"
                              : "bg-green-100 text-green-700"
                          }`}>
                            {!isAvail
                              ? "Hết hàng"
                              : isLow
                              ? `Còn ${branch.quantity_available}`
                              : `Còn ${branch.quantity_available}`}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* All branches out of stock message */}
                {allBranches.length > 0 && allBranches.every((b) => b.quantity_available === 0) && (
                  <p className="text-sm text-red-600 mt-3 text-center font-medium">
                    ⚠ Tất cả chi nhánh đã hết hàng hôm nay.
                  </p>
                )}
              </div>
            )}


            {/* Price Breakdown — only for cake (has sizes/flavors) */}
            {isCake && (
              <div className="bg-white rounded-xl p-4 sm:p-6 space-y-3 border border-mocha/5">
                <h2 className="text-sm font-semibold text-mocha mb-2">Chi tiết giá</h2>
                <div className="flex justify-between text-sm text-mocha/70">
                  <span>Giá cơ bản ({selectedSize || "—"})</span>
                  <span>{formatPrice(getSelectedSizePrice())}</span>
                </div>
                {getSelectedFlavorCost() > 0 && (
                  <div className="flex justify-between text-sm text-mocha/70">
                    <span>Hương vị ({selectedFlavor})</span>
                    <span>+{formatPrice(getSelectedFlavorCost())}</span>
                  </div>
                )}
                <div className="border-t border-mocha/10 pt-3 flex justify-between">
                  <span className="font-semibold text-mocha">Tổng cộng</span>
                  <span className="font-bold text-lg text-pink-pastel">{formatPrice(totalPrice)}</span>
                </div>
              </div>
            )}


            {/* Sweet product: show price simply */}
            {isSweet && (
              <div className="flex items-baseline gap-3">
                <span className="font-heading text-3xl font-bold text-pink-pastel">{formatPrice(product.base_price)}</span>
                <span className="text-mocha/50 text-sm">/ cái</span>
              </div>
            )}

            {/* Action Buttons — split by product type */}
            <div className="space-y-3">
              {isSweet && (
                <>
                  {/* Stock indicators — only shown when relevant (low/out) */}
                  {isOutOfStock && (
                    <div className="flex items-center gap-2 text-sm font-medium px-4 py-2.5 rounded-xl border bg-red-50 border-red-200 text-red-600">
                      <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span className="font-semibold">
                        {selectedBranch ? `${selectedBranch.branch_name} hết hàng` : "Hết hàng hôm nay"}
                      </span>
                    </div>
                  )}

                  {isLowStock && (
                    <div className="flex items-center gap-2 text-sm font-medium px-4 py-2.5 rounded-xl border bg-amber-50 border-amber-200 text-amber-700">
                      <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      <span>Sắp hết! Chỉ còn {selectedBranchStock} cái tại {selectedBranch?.branch_name ?? "chi nhánh này"}</span>
                    </div>
                  )}

                  {/* Mua ngay — trực tiếp checkout không cần admin duyệt */}
                  <button
                    id={`buy-now-${product.id}`}
                    onClick={handleBuyNow}
                    disabled={isOutOfStock}
                    className={`w-full py-3 px-6 font-semibold rounded-full transition-all min-h-[44px] shadow-sm hover:shadow-md active:scale-[0.98] ${
                      isOutOfStock
                        ? "bg-gray-200 text-gray-400 cursor-not-allowed"
                        : "bg-pink-pastel text-white hover:bg-pink-pastel/90"
                    }`}
                    aria-label={isOutOfStock ? "Hết hàng" : `Mua ${product.name} ngay`}
                  >
                    {isOutOfStock ? (
                      "Hết hàng"
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Mua ngay
                      </span>
                    )}
                  </button>

                  {/* Thêm vào giỏ */}
                  <button
                    id={`add-to-cart-${product.id}`}
                    onClick={handleAddToCart}
                    disabled={isOutOfStock}
                    className={`w-full py-2.5 px-6 font-medium rounded-full transition-all min-h-[44px] border ${
                      isOutOfStock
                        ? "bg-gray-100 text-gray-400 border-gray-200 cursor-not-allowed"
                        : addedToCart
                          ? "bg-green-50 text-green-600 border-green-200"
                          : "bg-white text-mocha border-mocha/20 hover:border-pink-pastel hover:text-pink-pastel"
                    }`}
                    aria-label={isOutOfStock ? "Hết hàng" : `Thêm ${product.name} vào giỏ hàng`}
                  >
                    {addedToCart ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                        </svg>
                        Đã thêm vào giỏ!
                      </span>
                    ) : (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4zM3 6h18M16 10a4 4 0 01-8 0" />
                        </svg>
                        Thêm vào giỏ
                      </span>
                    )}
                  </button>

                  {addedToCart && (
                    <button
                      onClick={openCart}
                      className="w-full py-2 px-6 text-sm font-medium text-pink-pastel border border-pink-pastel/30 rounded-full hover:bg-pink-pastel/5 transition-colors"
                    >
                      Xem giỏ hàng →
                    </button>
                  )}
                </>
              )}

              {isCake && (
                <>
                  <Link
                    href="/checkout"
                    id={`order-cake-${product.id}`}
                    className="w-full block text-center py-3 px-6 font-semibold rounded-full bg-pink-pastel text-white hover:bg-pink-pastel/90 transition-all shadow-sm hover:shadow-md active:scale-[0.98]"
                  >
                    <span className="flex items-center justify-center gap-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                      Đặt hàng ngay
                    </span>
                  </Link>
                  <Link
                    href="/cake-builder"
                    id={`design-cake-${product.id}`}
                    className="w-full block text-center py-2.5 px-6 text-sm font-medium text-mocha border border-mocha/20 rounded-full hover:bg-mocha/5 transition-colors"
                  >
                    ✨ Thiết kế bánh theo ý muốn
                  </Link>
                </>
              )}
            </div>

            {/* Reviews Section */}
            <ReviewsSection productId={product.id} />
          </section>
        </div>
      </div>
    </main>
  );
}

"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import { ProductDetailResponse } from "@/types";
import StarRating from "@/components/StarRating";

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(price);
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
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

function ReviewsSection({ productId }: { productId: string }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [reviewCount, setReviewCount] = useState(0);
  const [avgRating, setAvgRating] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchReviews = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page: page.toString(), page_size: "10" });
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
  }, [productId, page]);

  useEffect(() => {
    fetchReviews();
  }, [fetchReviews]);

  return (
    <section className="pt-6 border-t border-mocha/10" aria-label="Đánh giá">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-heading text-xl font-bold text-mocha">
          Đánh giá ({reviewCount})
        </h2>
        {avgRating && (
          <div className="flex items-center gap-1">
            <span className="text-yellow-500 text-lg">⭐</span>
            <span className="font-bold text-mocha">{avgRating.toFixed(1)}</span>
            <span className="text-mocha/50 text-sm">/5</span>
          </div>
        )}
      </div>

      {loading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="bg-cream rounded-xl p-4 animate-pulse">
              <div className="h-3 bg-mocha/10 rounded w-24 mb-2" />
              <div className="h-4 bg-mocha/10 rounded w-full" />
            </div>
          ))}
        </div>
      )}

      {!loading && reviews.length === 0 && (
        <p className="text-mocha/60 text-sm">
          Chưa có đánh giá nào. Hãy là người đầu tiên đánh giá sản phẩm này!
        </p>
      )}

      {!loading && reviews.length > 0 && (
        <div className="space-y-4">
          {reviews.map((review) => (
            <div key={review.id} className="bg-cream rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-mocha text-sm">{review.customer_name}</span>
                  <div className="flex">
                    {Array.from({ length: 5 }).map((_, i) => (
                      <span key={i} className={`text-sm ${i < review.rating ? "text-yellow-500" : "text-mocha/20"}`}>
                        ★
                      </span>
                    ))}
                  </div>
                </div>
                <span className="text-xs text-mocha/40">{formatDate(review.created_at)}</span>
              </div>
              {review.comment && (
                <p className="text-sm text-mocha/80">{review.comment}</p>
              )}
            </div>
          ))}

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

export default function ProductDetailPage() {
  const params = useParams();
  const productId = params.id as string;

  const [product, setProduct] = useState<ProductDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [selectedImageIndex, setSelectedImageIndex] = useState(0);
  const [selectedSize, setSelectedSize] = useState<string | null>(null);
  const [selectedFlavor, setSelectedFlavor] = useState<string | null>(null);
  const [imgErrors, setImgErrors] = useState<Set<number>>(new Set());

  useEffect(() => {
    async function fetchProduct() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.get<ProductDetailResponse>(
          `/api/v1/products/${productId}`
        );
        setProduct(data);
        // Default selections
        if (data.sizes.length > 0) {
          setSelectedSize(data.sizes[0].name);
        }
        if (data.flavors.length > 0) {
          setSelectedFlavor(data.flavors[0].name);
        }
      } catch {
        setError("Không thể tải thông tin sản phẩm. Vui lòng thử lại sau.");
      } finally {
        setLoading(false);
      }
    }
    if (productId) {
      fetchProduct();
    }
  }, [productId]);

  const handleImageError = (index: number) => {
    setImgErrors((prev) => new Set(prev).add(index));
  };

  // Calculate price breakdown
  const getSelectedSizePrice = (): number => {
    if (!product || !selectedSize) return product?.base_price ?? 0;
    const size = product.sizes.find((s) => s.name === selectedSize);
    return size?.price ?? product.base_price;
  };

  const getSelectedFlavorCost = (): number => {
    if (!product || !selectedFlavor) return 0;
    const flavor = product.flavors.find((f) => f.name === selectedFlavor);
    return flavor?.additional_cost ?? 0;
  };

  const totalPrice = getSelectedSizePrice() + getSelectedFlavorCost();

  // Loading skeleton
  if (loading) {
    return (
      <main className="min-h-screen bg-cream">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          <div className="animate-pulse">
            <div className="h-6 bg-gray-200 rounded w-32 mb-6" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Image skeleton */}
              <div>
                <div className="aspect-square bg-gray-200 rounded-2xl" />
                <div className="flex gap-2 mt-4">
                  {Array.from({ length: 4 }).map((_, i) => (
                    <div
                      key={i}
                      className="w-16 h-16 bg-gray-200 rounded-lg"
                    />
                  ))}
                </div>
              </div>
              {/* Info skeleton */}
              <div className="space-y-4">
                <div className="h-8 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/4" />
                <div className="h-4 bg-gray-200 rounded w-full" />
                <div className="h-4 bg-gray-200 rounded w-2/3" />
                <div className="h-10 bg-gray-200 rounded w-1/3 mt-6" />
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Error state
  if (error || !product) {
    return (
      <main className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-center px-4">
          <p className="text-mocha/70 text-lg mb-4">
            {error || "Không tìm thấy sản phẩm."}
          </p>
          <Link
            href="/products"
            className="inline-block px-6 py-2 bg-pink-pastel text-white rounded-full hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
          >
            Quay lại danh mục
          </Link>
        </div>
      </main>
    );
  }

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
            <li className="text-mocha font-medium truncate">
              {product.name}
            </li>
          </ol>
        </nav>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12">
          {/* Image Gallery */}
          <section aria-label="Hình ảnh sản phẩm">
            {/* Main Image */}
            <div className="aspect-square rounded-2xl overflow-hidden bg-gray-100 relative">
              {mainImage ? (
                <img
                  src={mainImage.url}
                  alt={product.name}
                  className="w-full h-full object-cover"
                  onError={() => handleImageError(selectedImageIndex)}
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
                    className={`flex-shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-lg overflow-hidden border-2 transition-colors min-w-[44px] min-h-[44px] ${
                      selectedImageIndex === index
                        ? "border-pink-pastel"
                        : "border-transparent hover:border-mocha/20"
                    }`}
                    aria-label={`Xem hình ${index + 1}`}
                    aria-current={selectedImageIndex === index ? "true" : undefined}
                  >
                    {!imgErrors.has(index) ? (
                      <img
                        src={image.url}
                        alt=""
                        className="w-full h-full object-cover"
                        onError={() => handleImageError(index)}
                        loading="lazy"
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
              <p className="text-mocha/80 leading-relaxed">
                {product.description}
              </p>
            )}

            {/* Size Selector */}
            {product.sizes.length > 0 && (
              <div>
                <h2 className="text-sm font-semibold text-mocha mb-3">
                  Kích thước
                </h2>
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
                <h2 className="text-sm font-semibold text-mocha mb-3">
                  Hương vị
                </h2>
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
                      {flavor.additional_cost > 0 &&
                        ` (+${formatPrice(flavor.additional_cost)})`}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Price Breakdown */}
            <div className="bg-white rounded-xl p-4 sm:p-6 space-y-3 border border-mocha/5">
              <h2 className="text-sm font-semibold text-mocha mb-2">
                Chi tiết giá
              </h2>
              <div className="flex justify-between text-sm text-mocha/70">
                <span>
                  Giá cơ bản ({selectedSize || "—"})
                </span>
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
                <span className="font-bold text-lg text-pink-pastel">
                  {formatPrice(totalPrice)}
                </span>
              </div>
            </div>

            {/* Order Button */}
            <button
              className="w-full py-3 px-6 bg-pink-pastel text-white font-semibold rounded-full hover:bg-pink-pastel/90 transition-colors min-h-[44px] shadow-sm hover:shadow-md"
              aria-label={`Đặt hàng ${product.name}`}
            >
              Đặt hàng
            </button>

            {/* Reviews Section */}
            <ReviewsSection productId={productId} />
          </section>
        </div>
      </div>
    </main>
  );
}

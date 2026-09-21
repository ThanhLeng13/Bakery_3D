"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import StarRating from "./StarRating";
import { ProductListItem } from "@/types";

interface ProductCardProps {
  product: ProductListItem;
}

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
  }).format(price);
}

export default function ProductCard({ product }: ProductCardProps) {
  const [imgError, setImgError] = useState(false);

  const shortDescription = product.description
    ? product.description.length > 100
      ? product.description.slice(0, 97) + "..."
      : product.description
    : "";

  return (
    <Link
      href={`/products/${product.id}`}
      className="card-lux group block focus:outline-none focus:ring-2 focus:ring-action focus:ring-offset-2 animate-fade-in"
    >
      {/* Image – CLS-safe: explicit aspect ratio + next/image */}
      <div className="aspect-square relative bg-subtle overflow-hidden">
        {product.image_url && !imgError ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover"
            onError={() => setImgError(true)}
            loading="lazy"
            placeholder="blur"
            blurDataURL="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMSIgaGVpZ2h0PSIxIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxyZWN0IHdpZHRoPSIxIiBoZWlnaHQ9IjEiIGZpbGw9IiNmNWY1ZjQiLz48L3N2Zz4="
          />
        ) : (
          // Placeholder fallback – maintains same layout, prevents CLS
          <div
            className="w-full h-full flex items-center justify-center bg-surface"
            role="img"
            aria-label={`Hình ảnh chưa có cho ${product.name}`}
          >
            <svg
              className="w-12 h-12 text-brand"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              strokeWidth={1.25}
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 8c-2.21 0-4 1.79-4 4h8c0-2.21-1.79-4-4-4zM5 12h14v2a4 4 0 01-4 4H9a4 4 0 01-4-4v-2zM9 8V6a3 3 0 016 0v2"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Nội dung thẻ.
          Tên bánh nét mảnh (font-normal) thay vì đậm: ở cỡ chữ này, độ đậm
          600 làm chữ nặng và kém thanh lịch. Giá tách khỏi tên bằng khoảng
          thở và một đường kẻ mảnh, để mắt đọc theo thứ tự tên → giá. */}
      <div className="p-5 sm:p-6">
        <h3 className="font-heading text-[1.0625rem] sm:text-lg font-normal text-ink leading-snug line-clamp-2">
          {product.name}
        </h3>

        {shortDescription && (
          <p className="mt-2 text-[0.8125rem] text-muted leading-relaxed line-clamp-2">
            {shortDescription}
          </p>
        )}

        <hr className="rule-fade my-4" />

        <div className="flex items-baseline justify-between gap-3">
          <p className="text-[0.9375rem] sm:text-base text-ink tracking-wide">
            {formatPrice(product.base_price)}
          </p>
          <StarRating
            rating={product.average_rating}
            reviewCount={product.review_count}
            size="sm"
          />
        </div>
      </div>
    </Link>
  );
}

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
      className="group block rounded-2xl bg-white border border-line shadow-sm hover:shadow-md hover:border-brand transition-all overflow-hidden focus:outline-none focus:ring-2 focus:ring-action focus:ring-offset-2 animate-fade-in"
    >
      {/* Image – CLS-safe: explicit aspect ratio + next/image */}
      <div className="aspect-square relative bg-subtle overflow-hidden">
        {product.image_url && !imgError ? (
          <Image
            src={product.image_url}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover group-hover:scale-105 transition-transform duration-300"
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
              className="w-16 h-16 text-muted"
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

      {/* Content */}
      <div className="p-4 sm:p-5 space-y-2">
        <h3 className="font-heading text-base sm:text-lg font-semibold text-ink line-clamp-1 transition-colors">
          {product.name}
        </h3>

        {shortDescription && (
          <p className="text-sm text-muted line-clamp-2">
            {shortDescription}
          </p>
        )}

        <p className="text-base sm:text-lg font-semibold text-ink">
          {formatPrice(product.base_price)}
        </p>

        <StarRating
          rating={product.average_rating}
          reviewCount={product.review_count}
          size="sm"
        />
      </div>
    </Link>
  );
}

"use client";

import { useState } from "react";
import Link from "next/link";
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
      className="group block rounded-2xl bg-white shadow-sm hover:shadow-md transition-shadow overflow-hidden focus:outline-none focus:ring-2 focus:ring-pink-pastel focus:ring-offset-2"
    >
      {/* Image */}
      <div className="aspect-square relative bg-gray-100 overflow-hidden">
        {product.image_url && !imgError ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={() => setImgError(true)}
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-cream">
            <svg
              className="w-16 h-16 text-mocha/20"
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
      <div className="p-4 space-y-2">
        <h3 className="font-heading text-base font-semibold text-mocha line-clamp-1 group-hover:text-pink-pastel transition-colors">
          {product.name}
        </h3>

        {shortDescription && (
          <p className="text-sm text-mocha/70 line-clamp-2">
            {shortDescription}
          </p>
        )}

        <p className="text-base font-semibold text-pink-pastel">
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

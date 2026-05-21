"use client";

/**
 * PriceDisplay component for the Cake Builder.
 * Shows price breakdown (base + toppings + decorations) and total price.
 * Updates within 200ms of any change with a subtle animated transition.
 *
 * Validates: Requirements 2.4, 2.5
 */

import type { PriceBreakdown } from "@/types";
import { formatPriceVND } from "@/lib/price-calculator";

interface PriceDisplayProps {
  priceBreakdown: PriceBreakdown;
}

export function PriceDisplay({ priceBreakdown }: PriceDisplayProps) {
  const { basePrice, toppingCost, decorationCost, totalPrice } =
    priceBreakdown;

  return (
    <div className="rounded-lg border border-pink-pastel/20 bg-cream p-4">
      <h3 className="mb-3 font-heading text-lg font-semibold text-mocha">
        Chi tiết giá
      </h3>

      <div className="space-y-2 text-sm font-body text-mocha/80">
        {/* Base price */}
        <div className="flex items-center justify-between">
          <span>Giá cơ bản</span>
          <span className="transition-all duration-200 ease-in-out">
            {formatPriceVND(basePrice)}
          </span>
        </div>

        {/* Topping cost - only show if > 0 */}
        {toppingCost > 0 && (
          <div className="flex items-center justify-between">
            <span>Topping</span>
            <span className="transition-all duration-200 ease-in-out">
              +{formatPriceVND(toppingCost)}
            </span>
          </div>
        )}

        {/* Decoration cost - only show if > 0 */}
        {decorationCost > 0 && (
          <div className="flex items-center justify-between">
            <span>Trang trí</span>
            <span className="transition-all duration-200 ease-in-out">
              +{formatPriceVND(decorationCost)}
            </span>
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-mocha/10 pt-2" />

        {/* Total price */}
        <div className="flex items-center justify-between">
          <span className="text-base font-semibold text-mocha">Tổng cộng</span>
          <span className="text-lg font-bold text-pink-pastel transition-all duration-200 ease-in-out">
            {formatPriceVND(totalPrice)}
          </span>
        </div>
      </div>
    </div>
  );
}

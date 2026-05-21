"use client";

/**
 * SizeSelector component for the Cake Builder.
 * Displays 4 size options with price per size and visual indicator for selection.
 * Responsive grid layout with 44×44px minimum touch targets.
 *
 * Validates: Requirements 2.4, 2.5
 */

import type { CakeSize } from "@/types";
import { BASE_PRICES, formatPriceVND } from "@/lib/price-calculator";

interface SizeSelectorProps {
  selectedSize: CakeSize;
  onSizeChange: (size: CakeSize) => void;
}

interface SizeOption {
  value: CakeSize;
  label: string;
  description: string;
}

const SIZE_OPTIONS: SizeOption[] = [
  { value: "16cm", label: "16cm", description: "4-6 người" },
  { value: "20cm", label: "20cm", description: "8-10 người" },
  { value: "24cm", label: "24cm", description: "12-15 người" },
  { value: "2-tier", label: "2 tầng", description: "20-25 người" },
];

export function SizeSelector({ selectedSize, onSizeChange }: SizeSelectorProps) {
  return (
    <div>
      <h3 className="mb-3 font-heading text-lg font-semibold text-mocha">
        Kích thước
      </h3>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {SIZE_OPTIONS.map((option) => {
          const isSelected = selectedSize === option.value;
          const price = BASE_PRICES[option.value];

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onSizeChange(option.value)}
              className={`
                min-h-[44px] min-w-[44px] rounded-lg border-2 p-3
                text-center transition-all duration-150 ease-in-out
                focus:outline-none focus:ring-2 focus:ring-pink-pastel/50
                ${
                  isSelected
                    ? "border-pink-pastel bg-pink-pastel/10 shadow-sm"
                    : "border-mocha/20 bg-white hover:border-pink-pastel/50 hover:bg-cream"
                }
              `}
              aria-pressed={isSelected}
              aria-label={`Kích thước ${option.label} - ${formatPriceVND(price)}`}
            >
              <div
                className={`font-heading text-base font-bold ${
                  isSelected ? "text-pink-pastel" : "text-mocha"
                }`}
              >
                {option.label}
              </div>
              <div className="mt-1 font-body text-xs text-mocha/60">
                {option.description}
              </div>
              <div
                className={`mt-1 font-body text-sm font-medium ${
                  isSelected ? "text-pink-pastel" : "text-mocha/80"
                }`}
              >
                {formatPriceVND(price)}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

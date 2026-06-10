/**
 * Pure function for cake price calculation.
 * Calculates total price based on size, toppings, and decorations.
 *
 * Validates: Requirements 2.4, 2.5
 */

import type { CakeSize, CakeDesign, PriceBreakdown } from "@/types";

/** Base prices by cake size (VND) */
export const BASE_PRICES: Record<CakeSize, number> = {
  "16cm": 250_000,
  "20cm": 350_000,
  "24cm": 450_000,
  "2-tier": 650_000,
};

/** Topping costs (VND) */
export const TOPPING_COSTS: Record<string, number> = {
  flowers: 80_000,
  fruits: 60_000,
  "chocolate drip": 50_000,
  sprinkles: 30_000,
  macarons: 100_000,
  text: 40_000,
};

/** Decoration costs (VND) */
export const DECORATION_COSTS: Record<string, number> = {
  piping: 30_000,
  rosettes: 50_000,
  sprinkles: 20_000,
  ribbon: 25_000,
  pearls: 45_000,
};

/**
 * Calculate the base price for a given cake size.
 */
export function getBasePrice(size: CakeSize): number {
  return BASE_PRICES[size] ?? 0;
}

/**
 * Calculate the topping cost from an array of topping types.
 * Returns 0 if no toppings selected. Sums cost of all selected toppings.
 */
export function getToppingCost(toppingType?: string | string[]): number {
  if (!toppingType) return 0;
  if (Array.isArray(toppingType)) {
    return toppingType.reduce((sum, t) => sum + (TOPPING_COSTS[t.toLowerCase()] ?? 0), 0);
  }
  return TOPPING_COSTS[toppingType.toLowerCase()] ?? 0;
}

/**
 * Calculate the total decoration cost from zone customizations.
 * Sums up decoration costs from all zones (top, body, border).
 */
export function getDecorationCost(zones: CakeDesign["zones"]): number {
  let cost = 0;

  const allDecorations = [
    zones.top?.decoration,
    zones.body?.decoration,
    zones.border?.decoration,
  ];

  for (const decoration of allDecorations) {
    if (decoration) {
      cost += DECORATION_COSTS[decoration.toLowerCase()] ?? 0;
    }
  }

  return cost;
}

/**
 * Calculate the full price breakdown for a cake design.
 * Pure function: basePrice + toppingCost + decorationCost = totalPrice
 */
export function calculatePrice(design: CakeDesign): PriceBreakdown {
  const basePrice = getBasePrice(design.size);
  const toppingCost = getToppingCost(design.topping_type);
  const decorationCost = getDecorationCost(design.zones);
  const totalPrice = basePrice + toppingCost + decorationCost;

  return {
    basePrice,
    toppingCost,
    decorationCost,
    totalPrice,
  };
}

/**
 * Format a price in VND currency format.
 * Example: 350000 → "350.000₫"
 */
export function formatPriceVND(price: number): string {
  return price.toLocaleString("vi-VN") + "₫";
}

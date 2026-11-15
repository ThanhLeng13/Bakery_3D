/**
 * Pure function for cake price calculation.
 * Calculates total price based on size, toppings, and decorations.
 *
 * Validates: Requirements 2.4, 2.5
 */

import type { CakeSize, CakeDesign, PriceBreakdown } from "@/types";

/** Base prices by cake diameter (VND). Tiers are priced separately below. */
export const BASE_PRICES: Record<CakeSize, number> = {
  "16cm": 250_000,
  "20cm": 350_000,
  "24cm": 450_000,
  // Legacy key: orders saved before tiers moved to `model_slug` used this size.
  "2-tier": 650_000,
};

/** Bánh từ hai tầng trở lên, giá theo mẫu chứ không theo đường kính. */
export const TWO_TIER_BASE_PRICE = 650_000;

/** Số tầng suy ra từ `model_slug`, ví dụ `round-2-tier` → 2. */
export function tiersForModelSlug(slug?: string | null): number {
  if (typeof slug !== "string") return 0;
  const match = slug.trim().toLowerCase().match(/-(\d+)-tier/);
  return match ? Number(match[1]) : 0;
}

/** Số tầng của một thiết kế; thiết kế cũ dùng size "2-tier" vẫn được nhận. */
export function tiersForDesign(design: Pick<CakeDesign, "model_slug" | "size">): number {
  const tiers = tiersForModelSlug(design.model_slug);
  if (tiers) return tiers;
  return design.size === "2-tier" ? 2 : 0;
}

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
 * Calculate the base price for a cake design.
 *
 * Tiers belong to the chosen body model (`model_slug`). A two-tier cake used to
 * be expressed as `size: "2-tier"`, so designs saved that way keep the same
 * price. Diameter alone must not downgrade a tiered cake to the single-tier rate.
 */
export function getBasePriceForDesign(
  design: Pick<CakeDesign, "model_slug" | "size">,
): number {
  if (tiersForDesign(design) >= 2) return TWO_TIER_BASE_PRICE;
  return BASE_PRICES[design.size] ?? 0;
}

/**
 * Calculate the topping cost from an array of topping types.
 * Returns 0 if no toppings selected. Sums cost of all selected toppings.
 * Normalizes (trim + lowercase), filters non-string/falsy items, and
 * deduplicates via Set to prevent overcharging for duplicates or whitespace variants.
 */
export function getToppingCost(toppingType?: string | string[]): number {
  if (!toppingType) return 0;
  if (Array.isArray(toppingType)) {
    // Normalize → filter → deduplicate
    const unique = Array.from(new Set(
      toppingType
        .filter((t): t is string => typeof t === "string" && t.trim().length > 0)
        .map((t) => t.trim().toLowerCase())
    ));
    return unique.reduce((sum, key) => sum + (TOPPING_COSTS[key] ?? 0), 0);
  }
  if (typeof toppingType !== "string") return 0;
  return TOPPING_COSTS[toppingType.trim().toLowerCase()] ?? 0;
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
  const basePrice = getBasePriceForDesign(design);
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

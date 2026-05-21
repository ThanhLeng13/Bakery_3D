/**
 * Utility functions for Cake Builder localStorage persistence.
 * Handles saving, loading, and clearing CakeDesign state.
 *
 * Validates: Requirements 2.9, 2.10
 */

import type { CakeDesign, CakeSize } from "@/types";

export const STORAGE_KEY = "cake_builder_design";

/** Valid cake sizes for validation */
const VALID_SIZES: CakeSize[] = ["16cm", "20cm", "24cm", "2-tier"];

/**
 * Check if localStorage is accessible.
 * Tests both availability and write capability.
 */
export function isLocalStorageAvailable(): boolean {
  try {
    const testKey = "__cake_storage_test__";
    localStorage.setItem(testKey, "1");
    localStorage.removeItem(testKey);
    return true;
  } catch {
    return false;
  }
}

/**
 * Validate that a parsed object matches the CakeDesign shape.
 * Returns true only if all required fields are present and correctly typed.
 */
function isValidCakeDesign(data: unknown): data is CakeDesign {
  if (data === null || typeof data !== "object") return false;

  const obj = data as Record<string, unknown>;

  // Validate size
  if (!VALID_SIZES.includes(obj.size as CakeSize)) return false;

  // Validate required string fields
  if (typeof obj.flavor !== "string") return false;
  if (typeof obj.cream_type !== "string") return false;
  if (typeof obj.cream_color !== "string") return false;

  // Validate optional fields
  if (
    obj.topping_type !== undefined &&
    obj.topping_type !== null &&
    typeof obj.topping_type !== "string"
  )
    return false;
  if (
    obj.special_notes !== undefined &&
    obj.special_notes !== null &&
    typeof obj.special_notes !== "string"
  )
    return false;

  // Validate zones
  if (obj.zones === null || typeof obj.zones !== "object") return false;
  const zones = obj.zones as Record<string, unknown>;

  for (const zoneName of ["top", "body", "border"]) {
    const zone = zones[zoneName];
    if (zone === null || typeof zone !== "object") return false;

    const zoneObj = zone as Record<string, unknown>;
    // Each zone field is optional but must be string if present
    for (const field of ["color", "decoration", "topping"]) {
      if (
        zoneObj[field] !== undefined &&
        zoneObj[field] !== null &&
        typeof zoneObj[field] !== "string"
      )
        return false;
    }
  }

  return true;
}

/**
 * Save CakeDesign to localStorage.
 * Returns false if localStorage is unavailable or full (QuotaExceededError).
 */
export function saveCakeDesign(design: CakeDesign): boolean {
  try {
    const json = JSON.stringify(design);
    localStorage.setItem(STORAGE_KEY, json);
    return true;
  } catch {
    // QuotaExceededError or SecurityError
    return false;
  }
}

/**
 * Load CakeDesign from localStorage.
 * Returns null if not found, corrupted, or invalid shape.
 */
export function loadCakeDesign(): CakeDesign | null {
  try {
    const json = localStorage.getItem(STORAGE_KEY);
    if (json === null) return null;

    const parsed: unknown = JSON.parse(json);
    if (isValidCakeDesign(parsed)) {
      return parsed;
    }

    // Invalid shape — discard corrupted data
    localStorage.removeItem(STORAGE_KEY);
    return null;
  } catch {
    // JSON parse error or localStorage access error
    return null;
  }
}

/**
 * Remove saved CakeDesign from localStorage.
 */
export function clearCakeDesign(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Silently ignore errors on clear
  }
}

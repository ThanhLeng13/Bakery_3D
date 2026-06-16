"use client";

/**
 * Custom hook for Cake Builder state management.
 * Manages the full CakeDesign state, provides actions for customization,
 * and calculates price automatically on any state change.
 *
 * Validates: Requirements 2.4, 2.5
 */

import { useState, useCallback, useMemo } from "react";
import type {
  CakeSize,
  CakeDesign,
  PriceBreakdown,
  ZoneCustomization,
} from "@/types";
import { calculatePrice } from "@/lib/price-calculator";

export type ZoneName = "top" | "body" | "border";

export interface CakeBuilderActions {
  setSize: (size: CakeSize) => void;
  setFlavor: (flavor: string) => void;
  setCreamType: (creamType: string) => void;
  setCreamColor: (creamColor: string) => void;
  setToppingType: (toppingType: string) => void;
  toggleTopping: (toppingType: string) => void;
  setSpecialNotes: (notes: string) => void;
  setZoneCustomization: (
    zone: ZoneName,
    customization: Partial<ZoneCustomization>
  ) => void;
  resetDesign: () => void;
}

export interface UseCakeBuilderReturn {
  design: CakeDesign;
  priceBreakdown: PriceBreakdown;
  totalPrice: number;
  actions: CakeBuilderActions;
  isComplete: boolean;
}

const DEFAULT_DESIGN: CakeDesign = {
  size: "16cm",
  flavor: "",
  cream_type: "",
  cream_color: "",
  topping_type: undefined,
  special_notes: undefined,
  zones: {
    top: { toppings: [] },
    body: {},
    border: {},
  },
};

/**
 * Check if all mandatory fields are filled for design completion.
 * Size is always valid (typed as CakeSize union), but flavor, cream_type,
 * and cream_color must be non-empty strings.
 */
function checkIsComplete(design: CakeDesign): boolean {
  return (
    design.flavor !== "" &&
    design.cream_type !== "" &&
    design.cream_color !== ""
  );
}

export function useCakeBuilder(
  initialDesign?: Partial<CakeDesign>
): UseCakeBuilderReturn {
  const [design, setDesign] = useState<CakeDesign>({
    ...DEFAULT_DESIGN,
    ...initialDesign,
    zones: {
      // Deep-merge mỗi zone riêng lẻ để giữ lại giá trị mặc định (vd: toppings: [])
      // khi initialDesign chỉ cung cấp một phần zone (vd: top: {})
      top: { ...DEFAULT_DESIGN.zones.top, ...initialDesign?.zones?.top },
      body: { ...DEFAULT_DESIGN.zones.body, ...initialDesign?.zones?.body },
      border: { ...DEFAULT_DESIGN.zones.border, ...initialDesign?.zones?.border },
    },
  });

  // Price is calculated via useMemo — updates synchronously on state change
  // ensuring the displayed price updates within 200ms of any customization change
  const priceBreakdown = useMemo<PriceBreakdown>(
    () => calculatePrice(design),
    [design]
  );

  const totalPrice = priceBreakdown.totalPrice;

  const isComplete = useMemo(() => checkIsComplete(design), [design]);

  const setSize = useCallback((size: CakeSize) => {
    setDesign((prev) => ({ ...prev, size }));
  }, []);

  const setFlavor = useCallback((flavor: string) => {
    setDesign((prev) => ({ ...prev, flavor }));
  }, []);

  const setCreamType = useCallback((creamType: string) => {
    setDesign((prev) => ({ ...prev, cream_type: creamType }));
  }, []);

  const setCreamColor = useCallback((creamColor: string) => {
    setDesign((prev) => ({
      ...prev,
      cream_color: creamColor,
      zones: {
        ...prev.zones,
        // Only update zone color if user hasn't explicitly customized it
        body: prev.zones.body.customized
          ? prev.zones.body
          : { ...prev.zones.body, color: creamColor },
        top: prev.zones.top.customized
          ? prev.zones.top
          : { ...prev.zones.top, color: creamColor },
      },
    }));
  }, []);

  const setToppingType = useCallback((toppingType: string) => {
    setDesign((prev) => ({
      ...prev,
      topping_type: [toppingType],
      zones: {
        ...prev.zones,
        top: {
          ...prev.zones.top,
          toppings: [toppingType],
        },
      },
    }));
  }, []);

  const toggleTopping = useCallback((toppingType: string) => {
    setDesign((prev) => {
      const current = prev.zones?.top?.toppings ?? [];
      const exists = current.includes(toppingType);
      const next = exists
        ? current.filter((t) => t !== toppingType)
        : [...current, toppingType];
      return {
        ...prev,
        topping_type: next,
        zones: {
          ...prev.zones,
          top: {
            ...prev.zones.top,
            toppings: next,
          },
        },
      };
    });
  }, []);

  const setSpecialNotes = useCallback((notes: string) => {
    // Enforce max 200 characters
    const trimmed = notes.slice(0, 200);
    setDesign((prev) => ({ ...prev, special_notes: trimmed }));
  }, []);

  const setZoneCustomization = useCallback(
    (zone: ZoneName, customization: Partial<ZoneCustomization>) => {
      setDesign((prev) => {
        const next = {
          ...prev,
          zones: {
            ...prev.zones,
            [zone]: {
              ...prev.zones[zone],
              ...customization,
              // Mark zone as customized when user explicitly sets its color
              ...("color" in customization ? { customized: true } : {}),
            },
          },
        };

        if (zone === "top" && "toppings" in customization) {
          next.topping_type = customization.toppings;
        }

        return next;
      });
    },
    []
  );

  const resetDesign = useCallback(() => {
    setDesign(DEFAULT_DESIGN);
  }, []);

  const actions: CakeBuilderActions = useMemo(
    () => ({
      setSize,
      setFlavor,
      setCreamType,
      setCreamColor,
      setToppingType,
      toggleTopping,
      setSpecialNotes,
      setZoneCustomization,
      resetDesign,
    }),
    [
      setSize,
      setFlavor,
      setCreamType,
      setCreamColor,
      setToppingType,
      toggleTopping,
      setSpecialNotes,
      setZoneCustomization,
      resetDesign,
    ]
  );

  return {
    design,
    priceBreakdown,
    totalPrice,
    actions,
    isComplete,
  };
}

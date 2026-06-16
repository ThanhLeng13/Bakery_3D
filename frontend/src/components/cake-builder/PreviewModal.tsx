"use client";

/**
 * PreviewModal component for the Cake Builder.
 * Shows a visual preview of the final cake design with summary and pricing.
 * Provides "Order" and "Edit" actions.
 *
 * Validates: Requirements 2.8
 */

import { useEffect, useRef } from "react";
import CakeSVG from "./CakeSVG";
import type { CakeDesign, PriceBreakdown } from "@/types";
import { formatPriceVND } from "@/lib/price-calculator";

interface PreviewModalProps {
  design: CakeDesign;
  priceBreakdown: PriceBreakdown;
  isOpen: boolean;
  onClose: () => void;
  onOrder: () => void;
}

/** Map flavor IDs to display labels */
const FLAVOR_LABELS: Record<string, string> = {
  vanilla: "Vanilla",
  chocolate: "Chocolate",
  matcha: "Matcha",
  strawberry: "Strawberry",
  "red-velvet": "Red Velvet",
  taro: "Taro",
};

/** Map cream type IDs to display labels */
const CREAM_TYPE_LABELS: Record<string, string> = {
  buttercream: "Buttercream",
  "whipped-cream": "Whipped Cream",
  ganache: "Ganache",
  "cream-cheese": "Cream Cheese",
};

/** Map cream color hex to display labels */
const CREAM_COLOR_LABELS: Record<string, string> = {
  "#E8837A": "Hồng",
  "#FFFFFF": "Trắng",
  "#5C3D2E": "Socola",
  "#7AB648": "Matcha",
  "#FFF8DC": "Vani",
  "#B57EDC": "Lavender",
};

export function PreviewModal({
  design,
  priceBreakdown,
  isOpen,
  onClose,
  onOrder,
}: PreviewModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Trap focus and handle Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const flavorLabel = FLAVOR_LABELS[design.flavor] ?? design.flavor;
  const creamTypeLabel = CREAM_TYPE_LABELS[design.cream_type] ?? design.cream_type;
  const creamColorLabel = CREAM_COLOR_LABELS[design.cream_color] ?? design.cream_color;

  // Gather toppings and decorations from zones
  const toppings: string[] = [
    ...(design.zones?.top?.toppings ?? []),
  ];

  const decorations: string[] = [];
  if (design.zones?.top?.decoration) decorations.push(design.zones.top.decoration);
  if (design.zones?.body?.decoration) decorations.push(design.zones.body.decoration);
  if (design.zones?.border?.decoration) decorations.push(design.zones.border.decoration);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Xem trước thiết kế bánh"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal content */}
      <div
        ref={modalRef}
        className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-2xl"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-white/80 hover:bg-gray-100 transition-colors min-w-[44px] min-h-[44px]"
          aria-label="Đóng"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          >
            <path d="M4 4L12 12M12 4L4 12" />
          </svg>
        </button>

        {/* Preview image - render CakeSVG in fixed state */}
        <div className="bg-cream p-6 flex justify-center">
          <div className="w-64 h-64">
            <CakeSVG
              design={design}
              activeZone={null}
              hoveredZone={null}
              onZoneClick={() => {}}
              onZoneHover={() => {}}
            />
          </div>
        </div>

        {/* Summary */}
        <div className="p-5 space-y-4">
          <h2 className="font-heading text-xl font-bold text-mocha">
            Thiết kế của bạn
          </h2>

          <div className="space-y-2 text-sm text-mocha/80">
            <div className="flex justify-between">
              <span className="font-medium text-mocha">Kích thước:</span>
              <span>{design.size}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium text-mocha">Hương vị:</span>
              <span>{flavorLabel}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-medium text-mocha">Loại kem:</span>
              <span>{creamTypeLabel}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-medium text-mocha">Màu kem:</span>
              <span className="flex items-center gap-2">
                {creamColorLabel}
                <span
                  className="inline-block w-4 h-4 rounded-full border border-gray-300"
                  style={{ backgroundColor: design.cream_color }}
                />
              </span>
            </div>
            {toppings.length > 0 && (
              <div className="flex justify-between">
                <span className="font-medium text-mocha">Toppings:</span>
                <span className="capitalize">{toppings.join(", ")}</span>
              </div>
            )}
            {decorations.length > 0 && (
              <div className="flex justify-between">
                <span className="font-medium text-mocha">Trang trí:</span>
                <span className="capitalize">{decorations.join(", ")}</span>
              </div>
            )}
            {design.special_notes && (
              <div className="pt-2 border-t border-gray-100">
                <span className="font-medium text-mocha">Ghi chú:</span>
                <p className="mt-1 text-mocha/70 italic">
                  {design.special_notes}
                </p>
              </div>
            )}
          </div>

          {/* Price */}
          <div className="border-t border-gray-100 pt-3">
            <div className="flex justify-between items-center">
              <span className="text-base font-semibold text-mocha">
                Tổng cộng
              </span>
              <span className="text-xl font-bold text-pink-pastel">
                {formatPriceVND(priceBreakdown.totalPrice)}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 min-h-[44px] rounded-lg border-2 border-gray-200 px-4 py-2.5 text-sm font-semibold text-mocha transition-all duration-150 hover:border-pink-pastel/50 hover:bg-cream focus:outline-none focus:ring-2 focus:ring-pink-pastel/50"
            >
              Chỉnh sửa
            </button>
            <button
              type="button"
              onClick={onOrder}
              className="flex-1 min-h-[44px] rounded-lg bg-pink-pastel px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-all duration-150 hover:bg-pink-pastel/90 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 active:scale-[0.98]"
            >
              Đặt hàng
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

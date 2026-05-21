"use client";

import { useCallback, useEffect, useRef } from "react";
import type { CakeZone } from "./CakeSVG";
import { CREAM_COLORS } from "./CakeSVG";
import type { ZoneCustomization } from "@/types";

interface OptionsPanelProps {
  activeZone: CakeZone | null;
  zoneCustomization: ZoneCustomization;
  onOptionSelect: (zone: CakeZone, option: Partial<ZoneCustomization>) => void;
  onClose: () => void;
}

/** Available topping options */
const TOPPING_OPTIONS = [
  { id: "flowers", label: "Hoa", icon: "🌸" },
  { id: "fruits", label: "Trái cây", icon: "🍓" },
  { id: "chocolate drip", label: "Chocolate drip", icon: "🍫" },
  { id: "sprinkles", label: "Sprinkles", icon: "✨" },
  { id: "macarons", label: "Macarons", icon: "🧁" },
  { id: "text", label: "Chữ viết", icon: "✍️" },
] as const;

/** Available border decoration options */
const BORDER_OPTIONS = [
  { id: "piping", label: "Piping", icon: "〰️" },
  { id: "rosettes", label: "Rosettes", icon: "🌹" },
  { id: "sprinkles", label: "Sprinkles", icon: "✨" },
  { id: "ribbon", label: "Ribbon", icon: "🎀" },
  { id: "pearls", label: "Pearls", icon: "⚪" },
] as const;

/** Available body pattern options */
const BODY_PATTERN_OPTIONS = [
  { id: "stripes", label: "Sọc", icon: "║" },
  { id: "dots", label: "Chấm bi", icon: "●" },
  { id: "waves", label: "Sóng", icon: "〜" },
] as const;

/** Cream color entries for display */
const CREAM_COLOR_ENTRIES = Object.entries(CREAM_COLORS).map(([name, hex]) => ({
  id: hex,
  name,
  label:
    name === "pink"
      ? "Hồng"
      : name === "white"
        ? "Trắng"
        : name === "chocolate"
          ? "Socola"
          : name === "matcha"
            ? "Matcha"
            : name === "vanilla"
              ? "Vani"
              : "Lavender",
}));

export default function OptionsPanel({
  activeZone,
  zoneCustomization,
  onOptionSelect,
  onClose,
}: OptionsPanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(event.target as Node)
      ) {
        // Check if click is on the SVG (zone click will handle it)
        const target = event.target as HTMLElement;
        if (target.closest("svg")) return;
        onClose();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  const handleColorSelect = useCallback(
    (color: string) => {
      if (!activeZone) return;
      onOptionSelect(activeZone, { color });
    },
    [activeZone, onOptionSelect]
  );

  const handleToppingSelect = useCallback(
    (topping: string) => {
      if (!activeZone) return;
      const newTopping = zoneCustomization.topping === topping ? undefined : topping;
      onOptionSelect(activeZone, { topping: newTopping });
    },
    [activeZone, zoneCustomization.topping, onOptionSelect]
  );

  const handleDecorationSelect = useCallback(
    (decoration: string) => {
      if (!activeZone) return;
      const newDecoration = zoneCustomization.decoration === decoration ? undefined : decoration;
      onOptionSelect(activeZone, { decoration: newDecoration });
    },
    [activeZone, zoneCustomization.decoration, onOptionSelect]
  );

  if (!activeZone) return null;

  const renderTopOptions = () => (
    <div className="space-y-4">
      {/* Topping selector */}
      <div>
        <h4 className="text-sm font-medium text-mocha mb-2">Toppings</h4>
        <div className="grid grid-cols-3 gap-2">
          {TOPPING_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => handleToppingSelect(option.id)}
              className={`flex flex-col items-center justify-center p-2 rounded-lg border-2 transition-all duration-100 min-w-[44px] min-h-[44px] ${
                zoneCustomization.topping === option.id
                  ? "border-pink-pastel bg-pink-pastel/10 shadow-sm"
                  : "border-gray-200 hover:border-pink-pastel/50 hover:bg-cream"
              }`}
              aria-label={`Topping: ${option.label}`}
              aria-pressed={zoneCustomization.topping === option.id}
            >
              <span className="text-lg" role="img" aria-hidden="true">
                {option.icon}
              </span>
              <span className="text-xs mt-1 text-mocha">{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Top zone color */}
      <div>
        <h4 className="text-sm font-medium text-mocha mb-2">Màu kem mặt trên</h4>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              onClick={() => handleColorSelect(color.id)}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                zoneCustomization.color === color.id
                  ? "border-pink-pastel scale-110 shadow-md"
                  : "border-gray-300 hover:scale-105 hover:border-pink-pastel/50"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu ${color.label}`}
              aria-pressed={zoneCustomization.color === color.id}
              title={color.label}
            >
              {zoneCustomization.color === color.id && (
                <span className="text-xs font-bold" style={{ color: color.name === "white" || color.name === "vanilla" ? "#5C3D2E" : "#FFF" }}>
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const renderBodyOptions = () => (
    <div className="space-y-4">
      {/* Cream color */}
      <div>
        <h4 className="text-sm font-medium text-mocha mb-2">Màu kem</h4>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              onClick={() => handleColorSelect(color.id)}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                zoneCustomization.color === color.id
                  ? "border-pink-pastel scale-110 shadow-md"
                  : "border-gray-300 hover:scale-105 hover:border-pink-pastel/50"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu ${color.label}`}
              aria-pressed={zoneCustomization.color === color.id}
              title={color.label}
            >
              {zoneCustomization.color === color.id && (
                <span className="text-xs font-bold" style={{ color: color.name === "white" || color.name === "vanilla" ? "#5C3D2E" : "#FFF" }}>
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Pattern */}
      <div>
        <h4 className="text-sm font-medium text-mocha mb-2">Hoa văn</h4>
        <div className="grid grid-cols-3 gap-2">
          {BODY_PATTERN_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => handleDecorationSelect(option.id)}
              className={`flex flex-col items-center justify-center p-2 rounded-lg border-2 transition-all duration-100 min-w-[44px] min-h-[44px] ${
                zoneCustomization.decoration === option.id
                  ? "border-pink-pastel bg-pink-pastel/10 shadow-sm"
                  : "border-gray-200 hover:border-pink-pastel/50 hover:bg-cream"
              }`}
              aria-label={`Hoa văn: ${option.label}`}
              aria-pressed={zoneCustomization.decoration === option.id}
            >
              <span className="text-lg">{option.icon}</span>
              <span className="text-xs mt-1 text-mocha">{option.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const renderBorderOptions = () => (
    <div className="space-y-4">
      {/* Border decorations */}
      <div>
        <h4 className="text-sm font-medium text-mocha mb-2">Viền trang trí</h4>
        <div className="grid grid-cols-3 gap-2">
          {BORDER_OPTIONS.map((option) => (
            <button
              key={option.id}
              onClick={() => handleDecorationSelect(option.id)}
              className={`flex flex-col items-center justify-center p-2 rounded-lg border-2 transition-all duration-100 min-w-[44px] min-h-[44px] ${
                zoneCustomization.decoration === option.id
                  ? "border-pink-pastel bg-pink-pastel/10 shadow-sm"
                  : "border-gray-200 hover:border-pink-pastel/50 hover:bg-cream"
              }`}
              aria-label={`Viền: ${option.label}`}
              aria-pressed={zoneCustomization.decoration === option.id}
            >
              <span className="text-lg" role="img" aria-hidden="true">
                {option.icon}
              </span>
              <span className="text-xs mt-1 text-mocha">{option.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Border color */}
      <div>
        <h4 className="text-sm font-medium text-mocha mb-2">Màu viền</h4>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              onClick={() => handleColorSelect(color.id)}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                zoneCustomization.color === color.id
                  ? "border-pink-pastel scale-110 shadow-md"
                  : "border-gray-300 hover:scale-105 hover:border-pink-pastel/50"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu ${color.label}`}
              aria-pressed={zoneCustomization.color === color.id}
              title={color.label}
            >
              {zoneCustomization.color === color.id && (
                <span className="text-xs font-bold" style={{ color: color.name === "white" || color.name === "vanilla" ? "#5C3D2E" : "#FFF" }}>
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const zoneTitle =
    activeZone === "top"
      ? "Mặt trên"
      : activeZone === "body"
        ? "Thân bánh"
        : "Viền bánh";

  return (
    <>
      {/* Desktop: Side panel */}
      <div
        ref={panelRef}
        className={`
          fixed md:relative
          bottom-0 left-0 right-0 md:bottom-auto md:left-auto md:right-auto
          md:w-[320px] md:min-w-[280px]
          bg-white rounded-t-2xl md:rounded-2xl
          shadow-xl md:shadow-lg
          border border-gray-100
          z-50 md:z-auto
          transform transition-transform duration-100 ease-out
          ${activeZone ? "translate-y-0" : "translate-y-full md:translate-y-0"}
          max-h-[60vh] md:max-h-[80vh]
          overflow-y-auto
        `}
        role="dialog"
        aria-label={`Tùy chỉnh ${zoneTitle}`}
        aria-modal="true"
      >
        {/* Mobile drag handle */}
        <div className="md:hidden flex justify-center pt-2 pb-1">
          <div className="w-10 h-1 bg-gray-300 rounded-full" />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
          <h3 className="font-heading text-lg text-mocha font-semibold">
            {zoneTitle}
          </h3>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors min-w-[44px] min-h-[44px]"
            aria-label="Đóng panel tùy chỉnh"
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
        </div>

        {/* Options content */}
        <div className="p-4">
          {activeZone === "top" && renderTopOptions()}
          {activeZone === "body" && renderBodyOptions()}
          {activeZone === "border" && renderBorderOptions()}
        </div>
      </div>

      {/* Mobile backdrop */}
      {activeZone && (
        <div
          className="fixed inset-0 bg-black/20 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
    </>
  );
}

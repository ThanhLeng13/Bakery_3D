"use client";

import { useCallback, useEffect } from "react";
import type { CakeZone } from "./CakeSVG";
import { CREAM_COLORS } from "./CakeSVG";
import type { ZoneCustomization } from "@/types";

interface OptionsPanelProps {
  activeZone: CakeZone | null;
  zoneCustomization: ZoneCustomization;
  onOptionSelect: (zone: CakeZone, option: Partial<ZoneCustomization>) => void;
  onClose: () => void;
  variant?: "sheet" | "inline";
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

function getToppingLabel(topping: string): string {
  return TOPPING_OPTIONS.find((option) => option.id === topping)?.label ?? topping;
}

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
  variant = "sheet",
}: OptionsPanelProps) {
  // Close panel when clicking outside
  useEffect(() => {
    if (variant === "inline") return;

    const handleClickOutside = (event: MouseEvent) => {
      // Guard: not an Element (e.g. Text node)
      if (!(event.target instanceof Element)) return;
      const target = event.target;
      // Desktop and mobile render separate responsive panel instances. Ignore
      // interactions inside either instance so the hidden one cannot close the
      // visible panel and let the click fall through to controls underneath.
      if (target.closest("[data-options-panel]")) return;
      // Don't close when clicking on 3D canvas / zone selector
      if (target.closest("[data-cake3d]")) return;
      if (target.closest("canvas")) return;
      if (target.closest("[data-zone-selector]")) return;
      onClose();
    };

    // Use bubble phase (no capture) to avoid conflicting with React's synthetic event system.
    // mousedown fires before click so we still prevent accidental closes from fast drags.
    document.addEventListener("mousedown", handleClickOutside, false);
    return () => document.removeEventListener("mousedown", handleClickOutside, false);
  }, [onClose, variant]);

  // Close on Escape key
  useEffect(() => {
    if (variant === "inline") return;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose, variant]);

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
      const current = zoneCustomization.toppings ?? [];
      const exists = current.includes(topping);
      const newToppings = exists
        ? current.filter((t) => t !== topping)
        : [...current, topping];
      onOptionSelect(activeZone, { toppings: newToppings });
    },
    [activeZone, zoneCustomization.toppings, onOptionSelect]
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
      {/* Topping selector - multi-select */}
      <div>
        <h4 className="text-sm font-medium text-ink mb-1">Toppings</h4>
        <p className="text-xs text-muted mb-2">Chọn một hoặc nhiều topping 🎉</p>
        <div className={`grid ${variant === "inline" ? "grid-cols-2 gap-1 xl:grid-cols-3 xl:gap-2" : "grid-cols-3 gap-2"}`}>
          {TOPPING_OPTIONS.map((option) => {
            const selected = (zoneCustomization.toppings ?? []).includes(option.id);
            return (
              <button
                key={option.id}
                type="button"
                data-topping-option={option.id}
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => {
                  e.stopPropagation();
                  handleToppingSelect(option.id);
                }}
                className={`flex flex-col items-center justify-center p-2 rounded-lg border-2 transition-all duration-150 min-w-[44px] min-h-[44px] ${
                  selected
                    ? "border-brand bg-subtle shadow-sm scale-105 ring-2 ring-subtle"
                    : "border-line hover:border-line hover:bg-surface"
                }`}
                aria-label={`Topping: ${option.label}`}
                aria-pressed={selected}
              >
                <span className="text-xl relative" role="img" aria-hidden="true">
                  {option.icon}
                  {selected && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-action rounded-full flex items-center justify-center text-[9px] text-white font-bold shadow-sm">✓</span>
                  )}
                </span>
                <span className={`${variant === "inline" ? "text-[9px] xl:text-[10px] 2xl:text-[11px]" : "text-xs"} mt-1 font-medium ${ selected ? "text-ink" : "text-ink" }`}>{option.label}</span>
              </button>
            );
          })}
        </div>
        {/* Selected toppings summary */}
        {(zoneCustomization.toppings ?? []).length > 0 && (
          <p className="mt-2 text-xs text-ink font-medium bg-subtle rounded-lg px-3 py-1.5">
            ✓ Đã chọn: {(zoneCustomization.toppings ?? []).map(getToppingLabel).join(", ")}
          </p>
        )}
      </div>

      {/* Top zone color */}
      <div>
        <h4 className="text-sm font-medium text-ink mb-2">Màu kem mặt trên</h4>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              type="button"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); handleColorSelect(color.id); }}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                zoneCustomization.color === color.id
                  ? "border-brand scale-110 shadow-md ring-2 ring-subtle"
                  : "border-line hover:scale-105 hover:border-line"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu ${color.label}`}
              aria-pressed={zoneCustomization.color === color.id}
              title={color.label}
            >
              {zoneCustomization.color === color.id && (
                <span className="text-xs font-bold" style={{ color: color.name === "white" || color.name === "vanilla" ? "var(--foreground)" : "#FFF" }}>
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
        <h4 className="text-sm font-medium text-ink mb-2">Màu kem</h4>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              type="button"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); handleColorSelect(color.id); }}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                zoneCustomization.color === color.id
                  ? "border-brand scale-110 shadow-md ring-2 ring-subtle"
                  : "border-line hover:scale-105 hover:border-line"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu ${color.label}`}
              aria-pressed={zoneCustomization.color === color.id}
              title={color.label}
            >
              {zoneCustomization.color === color.id && (
                <span className="text-xs font-bold" style={{ color: color.name === "white" || color.name === "vanilla" ? "var(--foreground)" : "#FFF" }}>
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Pattern */}
      <div>
        <h4 className="text-sm font-medium text-ink mb-2">Hoa văn</h4>
        <div className={`grid ${variant === "inline" ? "grid-cols-2 gap-1 xl:grid-cols-3 xl:gap-2" : "grid-cols-3 gap-2"}`}>
          {BODY_PATTERN_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); handleDecorationSelect(option.id); }}
              className={`flex flex-col items-center justify-center p-2 rounded-lg border-2 transition-all duration-150 min-w-[44px] min-h-[44px] ${
                zoneCustomization.decoration === option.id
                  ? "border-brand bg-subtle shadow-sm scale-105 ring-2 ring-subtle"
                  : "border-line hover:border-line hover:bg-surface"
              }`}
              aria-label={`Hoa văn: ${option.label}`}
              aria-pressed={zoneCustomization.decoration === option.id}
            >
              <span className={`text-lg ${ zoneCustomization.decoration === option.id ? "scale-110" : "" }`}>{option.icon}</span>
              <span className={`${variant === "inline" ? "text-[9px] xl:text-[10px] 2xl:text-[11px]" : "text-xs"} mt-1 font-medium ${ zoneCustomization.decoration === option.id ? "text-ink" : "text-ink" }`}>{option.label}</span>
            </button>
          ))}
        </div>
        {zoneCustomization.decoration && (
          <p className="mt-2 text-xs text-ink font-medium bg-subtle rounded-lg px-3 py-1.5">
            ✓ Đã chọn: {zoneCustomization.decoration}
          </p>
        )}
      </div>
    </div>
  );

  const renderBorderOptions = () => (
    <div className="space-y-4">
      {/* Border decorations */}
      <div>
        <h4 className="text-sm font-medium text-ink mb-2">Viền trang trí</h4>
        <div className={`grid ${variant === "inline" ? "grid-cols-2 gap-1 xl:grid-cols-3 xl:gap-2" : "grid-cols-3 gap-2"}`}>
          {BORDER_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); handleDecorationSelect(option.id); }}
              className={`flex flex-col items-center justify-center p-2 rounded-lg border-2 transition-all duration-150 min-w-[44px] min-h-[44px] ${
                zoneCustomization.decoration === option.id
                  ? "border-brand bg-subtle shadow-sm scale-105 ring-2 ring-subtle"
                  : "border-line hover:border-line hover:bg-surface"
              }`}
              aria-label={`Viền: ${option.label}`}
              aria-pressed={zoneCustomization.decoration === option.id}
            >
              <span className="text-xl" role="img" aria-hidden="true">
                {option.icon}
              </span>
              <span className={`${variant === "inline" ? "text-[9px] xl:text-[10px] 2xl:text-[11px]" : "text-xs"} mt-1 font-medium ${ zoneCustomization.decoration === option.id ? "text-ink" : "text-ink" }`}>{option.label}</span>
            </button>
          ))}
        </div>
        {zoneCustomization.decoration && (
          <p className="mt-2 text-xs text-ink font-medium bg-subtle rounded-lg px-3 py-1.5">
            ✓ Đã chọn: {zoneCustomization.decoration}
          </p>
        )}
      </div>

      {/* Border color */}
      <div>
        <h4 className="text-sm font-medium text-ink mb-2">Màu viền</h4>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              type="button"
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); handleColorSelect(color.id); }}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center ${
                zoneCustomization.color === color.id
                  ? "border-brand scale-110 shadow-md ring-2 ring-subtle"
                  : "border-line hover:scale-105 hover:border-line"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu ${color.label}`}
              aria-pressed={zoneCustomization.color === color.id}
              title={color.label}
            >
              {zoneCustomization.color === color.id && (
                <span className="text-xs font-bold" style={{ color: color.name === "white" || color.name === "vanilla" ? "var(--foreground)" : "#FFF" }}>
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
        data-options-panel="true"
        className={
          variant === "inline"
            ? "relative w-full animate-fade-in"
            : `
          fixed md:relative
          bottom-0 left-0 right-0 md:bottom-auto md:left-auto md:right-auto
          md:w-[320px] md:min-w-[280px]
          bg-white rounded-t-2xl md:rounded-2xl
          shadow-xl md:shadow-lg
          border border-line
          z-50 md:z-auto
          transform transition-transform duration-100 ease-out
          ${activeZone ? "translate-y-0" : "translate-y-full md:translate-y-0"}
          max-h-[60vh] md:max-h-[80vh]
          overflow-y-auto
        `
        }
        role={variant === "inline" ? "group" : "dialog"}
        aria-label={`Tùy chỉnh ${zoneTitle}`}
        aria-modal={variant === "inline" ? undefined : "true"}
      >
        {variant === "sheet" && (
          <>
            {/* Mobile drag handle */}
            <div className="md:hidden flex justify-center pt-2 pb-1">
              <div className="w-10 h-1 bg-line rounded-full" />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-line">
              <h3 className="font-heading text-lg text-ink font-semibold">
                {zoneTitle}
              </h3>
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-subtle transition-colors min-w-[44px] min-h-[44px]"
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
          </>
        )}

        {/* Options content */}
        <div className={variant === "inline" ? "p-0" : "p-4"}>
          {activeZone === "top" && renderTopOptions()}
          {activeZone === "body" && renderBodyOptions()}
          {activeZone === "border" && renderBorderOptions()}
        </div>
      </div>

      {/* Mobile backdrop */}
      {variant === "sheet" && activeZone && (
        <div
          className="fixed inset-0 bg-black/20 z-40 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
    </>
  );
}

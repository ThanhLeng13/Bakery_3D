"use client";

/**
 * CompletionPanel component for the Cake Builder.
 * Provides flavor, cream type, cream color selectors, special notes,
 * and a "Complete Design" button with validation.
 *
 * Validates: Requirements 2.6, 2.7
 */

import { useState, useCallback } from "react";
import { CREAM_COLORS } from "./CakeSVG";
import type { CakeDesign } from "@/types";

interface CompletionPanelProps {
  design: CakeDesign;
  onFlavorChange: (flavor: string) => void;
  onCreamTypeChange: (creamType: string) => void;
  onCreamColorChange: (creamColor: string) => void;
  onSpecialNotesChange: (notes: string) => void;
  onComplete: () => void;
  /** Unique suffix to prevent duplicate IDs when rendered multiple times (desktop + mobile) */
  instanceId?: string;
}

/** Available flavor options */
const FLAVOR_OPTIONS = [
  { id: "vanilla", label: "Vanilla" },
  { id: "chocolate", label: "Chocolate" },
  { id: "matcha", label: "Matcha" },
  { id: "strawberry", label: "Strawberry" },
  { id: "red-velvet", label: "Red Velvet" },
  { id: "taro", label: "Taro" },
] as const;

/** Available cream type options */
const CREAM_TYPE_OPTIONS = [
  { id: "buttercream", label: "Buttercream" },
  { id: "whipped-cream", label: "Whipped Cream" },
  { id: "ganache", label: "Ganache" },
  { id: "cream-cheese", label: "Cream Cheese" },
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

export interface ValidationErrors {
  flavor?: string;
  cream_type?: string;
  cream_color?: string;
}

/**
 * Validate mandatory fields for cake design completion.
 * Returns an object with error messages for missing fields, or empty object if valid.
 */
export function validateDesign(design: CakeDesign): ValidationErrors {
  const errors: ValidationErrors = {};

  if (!design.flavor) {
    errors.flavor = "Vui lòng chọn hương vị";
  }
  if (!design.cream_type) {
    errors.cream_type = "Vui lòng chọn loại kem";
  }
  if (!design.cream_color) {
    errors.cream_color = "Vui lòng chọn màu kem";
  }

  return errors;
}

export function CompletionPanel({
  design,
  onFlavorChange,
  onCreamTypeChange,
  onCreamColorChange,
  onSpecialNotesChange,
  onComplete,
  instanceId = "default",
}: CompletionPanelProps) {
  const [errors, setErrors] = useState<ValidationErrors>({});

  const handleComplete = useCallback(() => {
    const validationErrors = validateDesign(design);

    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    // Clear errors and proceed
    setErrors({});
    onComplete();
  }, [design, onComplete]);

  const handleFlavorChange = useCallback(
    (flavor: string) => {
      onFlavorChange(flavor);
      // Clear error when user selects a value
      setErrors((prev) => {
        const next = { ...prev };
        delete next.flavor;
        return next;
      });
    },
    [onFlavorChange]
  );

  const handleCreamTypeChange = useCallback(
    (creamType: string) => {
      onCreamTypeChange(creamType);
      setErrors((prev) => {
        const next = { ...prev };
        delete next.cream_type;
        return next;
      });
    },
    [onCreamTypeChange]
  );

  const handleCreamColorChange = useCallback(
    (color: string) => {
      onCreamColorChange(color);
      setErrors((prev) => {
        const next = { ...prev };
        delete next.cream_color;
        return next;
      });
    },
    [onCreamColorChange]
  );

  const notesLength = design.special_notes?.length ?? 0;

  return (
    <div className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm space-y-5">
      <h3 className="font-heading text-xl font-bold text-mocha">
        Hoàn thiện thiết kế
      </h3>

      {/* Flavor selector */}
      <div>
        <label className="block text-sm font-medium text-mocha mb-2">
          Hương vị <span className="text-pink-pastel">*</span>
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {FLAVOR_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => handleFlavorChange(option.id)}
              className={`min-h-[44px] min-w-[44px] rounded-lg border-2 px-3 py-2 text-sm font-medium transition-all duration-100 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 ${
                design.flavor === option.id
                  ? "border-pink-pastel bg-pink-pastel/10 text-pink-pastel"
                  : "border-gray-200 text-mocha hover:border-pink-pastel/50 hover:bg-cream"
              }`}
              aria-pressed={design.flavor === option.id}
              aria-label={`Hương vị: ${option.label}`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {errors.flavor && (
          <p className="mt-1 text-sm text-red-500" role="alert">
            {errors.flavor}
          </p>
        )}
      </div>

      {/* Cream type selector */}
      <div>
        <label className="block text-sm font-medium text-mocha mb-2">
          Loại kem <span className="text-pink-pastel">*</span>
        </label>
        <div className="grid grid-cols-2 gap-2">
          {CREAM_TYPE_OPTIONS.map((option) => (
            <button
              key={option.id}
              type="button"
              onClick={() => handleCreamTypeChange(option.id)}
              className={`min-h-[44px] min-w-[44px] rounded-lg border-2 px-3 py-2 text-sm font-medium transition-all duration-100 focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 ${
                design.cream_type === option.id
                  ? "border-pink-pastel bg-pink-pastel/10 text-pink-pastel"
                  : "border-gray-200 text-mocha hover:border-pink-pastel/50 hover:bg-cream"
              }`}
              aria-pressed={design.cream_type === option.id}
              aria-label={`Loại kem: ${option.label}`}
            >
              {option.label}
            </button>
          ))}
        </div>
        {errors.cream_type && (
          <p className="mt-1 text-sm text-red-500" role="alert">
            {errors.cream_type}
          </p>
        )}
      </div>

      {/* Cream color selector */}
      <div>
        <label className="block text-sm font-medium text-mocha mb-2">
          Màu kem <span className="text-pink-pastel">*</span>
        </label>
        <div className="flex flex-wrap gap-2">
          {CREAM_COLOR_ENTRIES.map((color) => (
            <button
              key={color.id}
              type="button"
              onClick={() => handleCreamColorChange(color.id)}
              className={`w-9 h-9 rounded-full border-2 transition-all duration-100 min-w-[44px] min-h-[44px] flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 ${
                design.cream_color === color.id
                  ? "border-pink-pastel scale-110 shadow-md"
                  : "border-gray-300 hover:scale-105 hover:border-pink-pastel/50"
              }`}
              style={{ backgroundColor: color.id }}
              aria-label={`Màu kem: ${color.label}`}
              aria-pressed={design.cream_color === color.id}
              title={color.label}
            >
              {design.cream_color === color.id && (
                <span
                  className="text-xs font-bold"
                  style={{
                    color:
                      color.name === "white" || color.name === "vanilla"
                        ? "#5C3D2E"
                        : "#FFF",
                  }}
                >
                  ✓
                </span>
              )}
            </button>
          ))}
        </div>
        {errors.cream_color && (
          <p className="mt-1 text-sm text-red-500" role="alert">
            {errors.cream_color}
          </p>
        )}
      </div>

      {/* Special notes textarea */}
      <div>
        <label
          htmlFor={`special-notes-${instanceId}`}
          className="block text-sm font-medium text-mocha mb-2"
        >
          Ghi chú đặc biệt
        </label>
        <textarea
          id={`special-notes-${instanceId}`}
          value={design.special_notes ?? ""}
          onChange={(e) => onSpecialNotesChange(e.target.value)}
          maxLength={200}
          rows={3}
          placeholder="Ví dụ: Viết chữ 'Happy Birthday' trên mặt bánh..."
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-mocha placeholder:text-mocha/40 focus:border-pink-pastel focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 resize-none"
        />
        <p className="mt-1 text-xs text-mocha/50 text-right">
          {notesLength}/200
        </p>
      </div>

      {/* Complete button */}
      <button
        type="button"
        onClick={handleComplete}
        className="w-full min-h-[44px] rounded-lg bg-pink-pastel px-6 py-3 text-base font-semibold text-white shadow-sm transition-all duration-150 hover:bg-pink-pastel/90 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-pink-pastel/50 active:scale-[0.98]"
      >
        Hoàn thành thiết kế
      </button>
    </div>
  );
}

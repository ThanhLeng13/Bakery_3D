"use client";

import type { CakeDesign, CakeSize, ZoneCustomization } from "@/types";
import { BASE_PRICES, formatPriceVND } from "@/lib/price-calculator";
import OptionsPanel from "./OptionsPanel";
import { CREAM_COLORS, type CakeZone } from "./CakeSVG";

export type BuilderStep =
  | "size"
  | "flavor"
  | "cream"
  | "color"
  | CakeZone
  | "notes";

interface ConfiguratorRailProps {
  design: CakeDesign;
  activeStep: BuilderStep;
  activeZone: CakeZone | null;
  detailOpen: boolean;
  onStepChange: (step: BuilderStep) => void;
  onCloseDetail: () => void;
  onSizeChange: (size: CakeSize) => void;
  onFlavorChange: (flavor: string) => void;
  onCreamTypeChange: (creamType: string) => void;
  onCreamColorChange: (color: string) => void;
  onSpecialNotesChange: (notes: string) => void;
  onZoneOptionSelect: (
    zone: CakeZone,
    option: Partial<ZoneCustomization>,
  ) => void;
  onCloseZone: () => void;
}

const SIZE_OPTIONS: Array<{
  value: CakeSize;
  label: string;
  badge: string;
  description: string;
}> = [
  { value: "16cm", label: "16 cm", badge: "16", description: "4–6 người" },
  { value: "20cm", label: "20 cm", badge: "20", description: "8–10 người" },
  { value: "24cm", label: "24 cm", badge: "24", description: "12–15 người" },
  { value: "2-tier", label: "2 tầng", badge: "2T", description: "20–25 người" },
];

const FLAVOR_OPTIONS = [
  { id: "vanilla", label: "Vanilla", badge: "V" },
  { id: "chocolate", label: "Chocolate", badge: "C" },
  { id: "matcha", label: "Matcha", badge: "M" },
  { id: "strawberry", label: "Dâu", badge: "D" },
  { id: "red-velvet", label: "Red Velvet", badge: "R" },
  { id: "taro", label: "Khoai môn", badge: "K" },
] as const;

const CREAM_TYPE_OPTIONS = [
  { id: "buttercream", label: "Buttercream", badge: "B" },
  { id: "whipped-cream", label: "Whipped cream", badge: "W" },
  { id: "ganache", label: "Ganache", badge: "G" },
  { id: "cream-cheese", label: "Cream cheese", badge: "C" },
] as const;

const CREAM_COLOR_ENTRIES = Object.entries(CREAM_COLORS).map(([name, hex]) => ({
  id: hex,
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

const STEP_LABELS: Record<BuilderStep, string> = {
  size: "Kích thước",
  flavor: "Hương vị",
  cream: "Hương vị",
  color: "Màu sắc",
  top: "Topping",
  body: "Hoa văn",
  border: "Trang trí",
  notes: "Lời nhắn",
};

const OVERVIEW_STEPS: BuilderStep[] = [
  "size",
  "flavor",
  "color",
  "body",
  "border",
  "top",
  "notes",
];

function hasZoneCustomization(zone: ZoneCustomization | undefined): boolean {
  return Boolean(
    zone?.customized || zone?.decoration || (zone?.toppings?.length ?? 0) > 0,
  );
}

function isStepComplete(step: BuilderStep, design: CakeDesign): boolean {
  switch (step) {
    case "size":
      return Boolean(design.size);
    case "flavor":
    case "cream":
      return Boolean(design.flavor && design.cream_type);
    case "color":
      return Boolean(design.cream_color);
    case "top":
    case "body":
    case "border":
      return hasZoneCustomization(design.zones?.[step]);
    case "notes":
      return Boolean(design.special_notes?.trim());
  }
}

function DetailChoice({
  selected,
  badge,
  label,
  description,
  onClick,
}: {
  selected: boolean;
  badge: string;
  label: string;
  description?: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className="group relative flex min-h-[44px] w-full items-center gap-2.5 text-left md:min-h-[38px] xl:min-h-[44px] 2xl:min-h-[48px]"
    >
      <span
        className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-[10px] font-bold transition-colors xl:h-10 xl:w-10 xl:text-[11px] 2xl:h-11 2xl:w-11 2xl:text-xs ${
          selected
            ? "border-brand bg-action text-white"
            : "border-line bg-white/65 text-muted group-hover:border-brand"
        }`}
        aria-hidden="true"
      >
        {selected ? "✓" : badge}
      </span>
      <span className="min-w-0 truncate text-[10px] font-semibold uppercase tracking-[0.08em] text-muted xl:text-[11px] 2xl:text-xs">
        {label}
      </span>
      {description && (
        <span className="pointer-events-none absolute left-[calc(100%+10px)] top-1/2 z-40 hidden w-36 -translate-y-1/2 border border-line bg-white px-3 py-2 text-[10px] normal-case tracking-normal text-ink shadow-lg md:group-hover:block md:group-focus-visible:block xl:w-40 xl:text-[11px] 2xl:w-44 2xl:text-xs">
          <strong className="block font-semibold">{label}</strong>
          <span className="mt-0.5 block text-muted">{description}</span>
        </span>
      )}
    </button>
  );
}

export default function ConfiguratorRail({
  design,
  activeStep,
  activeZone,
  detailOpen,
  onStepChange,
  onCloseDetail,
  onSizeChange,
  onFlavorChange,
  onCreamTypeChange,
  onCreamColorChange,
  onSpecialNotesChange,
  onZoneOptionSelect,
  onCloseZone,
}: ConfiguratorRailProps) {
  const detailStep = activeStep === "cream" ? "flavor" : activeStep;

  if (!detailOpen) {
    return (
      <aside aria-label="Các bước cấu hình bánh" data-zone-selector="true">
        <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-ink xl:text-[11px] 2xl:text-xs">
          Tùy chỉnh
        </p>
        <nav className="mt-2.5 space-y-0.5">
          {OVERVIEW_STEPS.map((step) => {
            const complete = isStepComplete(step, design);

            return (
              <button
                key={step}
                type="button"
                onClick={() => onStepChange(step)}
                className="group flex min-h-[44px] w-full items-center gap-1.5 text-left text-[10px] font-medium uppercase tracking-[0.1em] text-muted transition-colors hover:text-ink md:min-h-[27px] xl:min-h-[31px] xl:text-[11px] 2xl:min-h-[36px] 2xl:text-xs"
              >
                <span
                  className={`w-2.5 text-[9px] xl:text-[10px] 2xl:text-[11px] ${
                    complete ? "text-ink" : "text-transparent"
                  }`}
                  aria-hidden="true"
                >
                  ✓
                </span>
                <span className="relative">
                  {STEP_LABELS[step]}
                  <span className="absolute inset-x-0 -bottom-1 h-px origin-left scale-x-0 bg-action transition-transform group-hover:scale-x-100" />
                </span>
              </button>
            );
          })}
        </nav>
      </aside>
    );
  }

  return (
    <aside
      aria-label={`Tùy chỉnh ${STEP_LABELS[detailStep]}`}
      data-zone-selector="true"
      className="animate-fade-in"
    >
      <button
        type="button"
        onClick={onCloseDetail}
        className="min-h-[36px] text-[9px] font-semibold uppercase tracking-[0.14em] text-muted transition-colors hover:text-ink xl:text-[10px] 2xl:text-[11px]"
      >
        ← Quay lại
      </button>
      <h2 className="mt-1 text-[11px] font-bold uppercase tracking-[0.18em] text-ink xl:text-xs 2xl:text-sm">
        {STEP_LABELS[detailStep]}
      </h2>

      <div className="mt-3">
        {detailStep === "size" && (
          <div className="space-y-1">
            {SIZE_OPTIONS.map((option) => (
              <DetailChoice
                key={option.value}
                selected={design.size === option.value}
                badge={option.badge}
                label={option.label}
                description={`${option.description} · ${formatPriceVND(BASE_PRICES[option.value])}`}
                onClick={() => onSizeChange(option.value)}
              />
            ))}
          </div>
        )}

        {detailStep === "flavor" && (
          <div className="space-y-4">
            <div>
              <p className="mb-1 text-[8px] font-bold uppercase tracking-[0.16em] text-muted xl:text-[9px] 2xl:text-[10px]">
                Cốt bánh
              </p>
              <div className="space-y-0.5">
                {FLAVOR_OPTIONS.map((option) => (
                  <DetailChoice
                    key={option.id}
                    selected={design.flavor === option.id}
                    badge={option.badge}
                    label={option.label}
                    onClick={() => onFlavorChange(option.id)}
                  />
                ))}
              </div>
            </div>
            <div>
              <p className="mb-1 text-[8px] font-bold uppercase tracking-[0.16em] text-muted xl:text-[9px] 2xl:text-[10px]">
                Loại kem
              </p>
              <div className="space-y-0.5">
                {CREAM_TYPE_OPTIONS.map((option) => (
                  <DetailChoice
                    key={option.id}
                    selected={design.cream_type === option.id}
                    badge={option.badge}
                    label={option.label}
                    onClick={() => onCreamTypeChange(option.id)}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {detailStep === "color" && (
          <div className="space-y-1">
            {CREAM_COLOR_ENTRIES.map((color) => {
              const selected = design.cream_color === color.id;

              return (
                <button
                  key={color.id}
                  type="button"
                  onClick={() => onCreamColorChange(color.id)}
                  aria-label={`Màu kem ${color.label}`}
                  aria-pressed={selected}
                  className="flex min-h-[44px] w-full items-center gap-2.5 text-left md:min-h-[38px] xl:min-h-[44px] 2xl:min-h-[48px]"
                >
                  <span
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 xl:h-10 xl:w-10 2xl:h-11 2xl:w-11 ${
                      selected
                        ? "border-brand ring-2 ring-subtle"
                        : "border-white shadow-sm"
                    }`}
                    style={{ backgroundColor: color.id }}
                    aria-hidden="true"
                  >
                    {selected && (
                      <span className="rounded-full bg-white/80 px-1 text-[9px] font-bold text-ink">
                        ✓
                      </span>
                    )}
                  </span>
                  <span className="text-[10px] font-semibold uppercase tracking-[0.08em] text-muted xl:text-[11px] 2xl:text-xs">
                    {color.label}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {(detailStep === "top" ||
          detailStep === "body" ||
          detailStep === "border") && (
          <OptionsPanel
            activeZone={activeZone}
            zoneCustomization={design.zones?.[detailStep] || {}}
            onOptionSelect={onZoneOptionSelect}
            onClose={onCloseZone}
            variant="inline"
          />
        )}

        {detailStep === "notes" && (
          <div>
            <textarea
              value={design.special_notes ?? ""}
              onChange={(event) => onSpecialNotesChange(event.target.value)}
              maxLength={200}
              rows={5}
              placeholder="Lời nhắn trên bánh..."
              aria-label="Lời nhắn trên bánh"
              className="w-full resize-none border border-line bg-white/70 px-2.5 py-2 text-xs text-ink placeholder:text-muted focus:border-brand focus:outline-none xl:text-[13px] 2xl:text-sm"
            />
            <p className="mt-1 text-right text-[9px] text-muted xl:text-[10px] 2xl:text-[11px]">
              {design.special_notes?.length ?? 0}/200
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}

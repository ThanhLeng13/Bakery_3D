"use client";

import type { Cake3DModel, Cake3DModelSlug } from "@/types";
import { getCakeBodyModel } from "@/lib/cake-body-models";

const MODEL_META: Record<Cake3DModelSlug, { badge: string; description: string }> = {
  "round-1-tier": { badge: "1T", description: "Mẫu cơ bản, linh hoạt trang trí" },
  "round-2-tier": { badge: "2T", description: "Phù hợp tiệc 20–25 khách" },
  "round-3-tier": { badge: "3T", description: "Tiệc cưới và sự kiện lớn" },
  "square-1-tier": { badge: "□", description: "Dáng vuông hiện đại" },
  "heart-1-tier": { badge: "♥", description: "Dành cho dịp kỷ niệm" },
  "tall-1-tier": { badge: "↕", description: "Dáng cao thanh lịch" },
};

interface CakeModelPickerProps {
  models: Cake3DModel[];
  selectedSlug: Cake3DModelSlug;
  loading?: boolean;
  error?: boolean;
  onSelect: (slug: Cake3DModelSlug) => void;
}

/**
 * Compact selector for the reusable .glb base model.
 * It deliberately only changes the base geometry: zone colors, piping and
 * toppings continue to be configured by the existing cake builder controls.
 */
export default function CakeModelPicker({
  models,
  selectedSlug,
  loading = false,
  error = false,
  onSelect,
}: CakeModelPickerProps) {
  return (
    <section aria-label="Chọn mẫu bánh 3D" className="border-t border-line pt-3">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-[11px] font-bold uppercase tracking-[0.18em] text-ink xl:text-xs 2xl:text-sm">
          Mẫu bánh 3D
        </h2>
        <span className="text-[9px] text-muted xl:text-[10px]">Kho mẫu thật</span>
      </div>

      {loading ? (
        <p className="mt-2 text-[10px] text-muted">Đang tải kho mẫu...</p>
      ) : error ? (
        <p className="mt-2 text-[10px] leading-relaxed text-muted">
          Chưa tải được kho mẫu. Đang dùng mẫu tròn mặc định.
        </p>
      ) : (
        <div className="mt-2 grid grid-cols-3 gap-1.5 xl:gap-2">
          {models.map((model) => {
            const meta = MODEL_META[model.slug] ?? { badge: "3D", description: "Mẫu bánh 3D" };
            const definition = getCakeBodyModel(model.slug);
            const selected = model.slug === selectedSlug;
            return (
              <button
                key={model.id}
                type="button"
                onClick={() => onSelect(model.slug)}
                aria-pressed={selected}
                title={meta.description}
                className={`min-h-[58px] border px-1.5 py-2 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/70 xl:min-h-[64px] ${
                  selected
                    ? "border-ink bg-ink text-white shadow-sm"
                    : "border-line bg-white/65 text-muted hover:border-brand hover:bg-white hover:text-ink"
                }`}
              >
                <span className="block font-heading text-base leading-none xl:text-lg" aria-hidden="true">
                  {meta.badge}
                </span>
                <span className="mt-1 block truncate text-[8px] font-semibold uppercase tracking-[0.06em] xl:text-[9px]">
                  {model.name.replace("Bánh ", "")}
                </span>
                {!definition.orderable && (
                  <span className={`mt-0.5 block text-[7px] font-medium normal-case tracking-normal ${selected ? "text-white/70" : "text-muted"}`}>
                    Xem mẫu
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}

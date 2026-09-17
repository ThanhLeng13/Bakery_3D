"use client";

import { useState } from "react";
import Link from "next/link";
import type { CakeDesign, PriceBreakdown } from "@/types";
import { formatPriceVND } from "@/lib/price-calculator";

interface OrderSummaryProps {
  design: CakeDesign;
  priceBreakdown: PriceBreakdown;
  validationMessage?: string | null;
  onContinue: () => void;
}

const FLAVOR_LABELS: Record<string, string> = {
  vanilla: "Vanilla",
  chocolate: "Chocolate",
  matcha: "Matcha",
  strawberry: "Dâu",
  "red-velvet": "Red Velvet",
  taro: "Khoai môn",
};

const CREAM_LABELS: Record<string, string> = {
  buttercream: "Buttercream",
  "whipped-cream": "Whipped cream",
  ganache: "Ganache",
  "cream-cheese": "Cream cheese",
};

const TOPPING_LABELS: Record<string, string> = {
  flowers: "Hoa",
  fruits: "Trái cây",
  "chocolate drip": "Chocolate drip",
  sprinkles: "Sprinkles",
  macarons: "Macarons",
  text: "Chữ viết",
};

const DECORATION_LABELS: Record<string, string> = {
  stripes: "Sọc",
  dots: "Chấm bi",
  waves: "Sóng",
  piping: "Piping",
  rosettes: "Rosettes",
  sprinkles: "Sprinkles",
  ribbon: "Ribbon",
  pearls: "Pearls",
};

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[88px_1fr] gap-2 py-0.5 text-[11px] leading-4 md:grid-cols-[52px_1fr] md:gap-1 md:text-[8px] md:leading-3 xl:grid-cols-[78px_1fr] xl:text-[10px] xl:leading-4 2xl:grid-cols-[92px_1fr] 2xl:gap-3 2xl:text-xs 2xl:leading-5">
      <dt className="text-muted">{label}</dt>
      <dd
        className="text-right font-medium text-ink md:truncate"
        title={value}
      >
        {value}
      </dd>
    </div>
  );
}

export default function OrderSummary({
  design,
  priceBreakdown,
  validationMessage,
  onContinue,
}: OrderSummaryProps) {
  const [showDetails, setShowDetails] = useState(true);
  const toppings = design.zones?.top?.toppings ?? [];
  const bodyDecoration = design.zones?.body?.decoration;
  const borderDecoration = design.zones?.border?.decoration;
  const decorationLabel = [bodyDecoration, borderDecoration]
    .filter(Boolean)
    .map((item) => DECORATION_LABELS[item as string] ?? item)
    .join(", ");

  return (
    <aside aria-label="Tóm tắt thiết kế bánh">
      <div className="flex items-baseline justify-between gap-2 border-b border-line pb-2">
        <h2 className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink md:text-[8px] xl:text-[10px] 2xl:text-xs">
          Bánh của bạn
        </h2>
        <p className="text-xs font-semibold tabular-nums text-ink md:text-[9px] xl:text-xs 2xl:text-sm">
          {formatPriceVND(priceBreakdown.totalPrice)}
        </p>
      </div>

      <p className="mt-2 text-[10px] leading-4 text-muted md:text-[7px] md:leading-3 xl:text-[9px] 2xl:text-[11px] 2xl:leading-4">
        Thời gian hoàn thiện dự kiến 24–48 giờ.
      </p>

      <button
        type="button"
        onClick={() => setShowDetails((current) => !current)}
        className="mt-2 min-h-[44px] text-left text-sm font-medium text-muted underline decoration-line underline-offset-4 transition-colors hover:text-ink hover:decoration-action"
        aria-expanded={showDetails}
      >
        {showDetails ? "Ẩn thành phần" : "Hiện thành phần"}
      </button>

      {showDetails && (
        <dl className="border-b border-line pb-2">
          <SummaryRow label="Kích thước" value={design.size} />
          <SummaryRow
            label="Hương vị"
            value={FLAVOR_LABELS[design.flavor] ?? "Chưa chọn"}
          />
          <SummaryRow
            label="Loại kem"
            value={CREAM_LABELS[design.cream_type] ?? "Chưa chọn"}
          />
          <SummaryRow
            label="Màu kem"
            value={design.cream_color ? "Đã chọn" : "Chưa chọn"}
          />
          <SummaryRow
            label="Topping"
            value={
              toppings.length
                ? toppings
                    .map((item) => TOPPING_LABELS[item] ?? item)
                    .join(", ")
                : "Không"
            }
          />
          <SummaryRow label="Trang trí" value={decorationLabel || "Cơ bản"} />
        </dl>
      )}

      <div className="space-y-1.5 border-b border-line py-3 text-sm text-muted">
        <div className="flex items-center justify-between gap-4">
          <span>Giá bánh</span>
          <span className="tabular-nums">
            {formatPriceVND(priceBreakdown.basePrice)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span>Topping</span>
          <span className="tabular-nums">
            {formatPriceVND(priceBreakdown.toppingCost)}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span>Trang trí</span>
          <span className="tabular-nums">
            {formatPriceVND(priceBreakdown.decorationCost)}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2 py-3">
        <span className="text-sm font-semibold text-ink">
          Tổng cộng
        </span>
        <span className="text-lg font-bold tabular-nums text-ink">
          {formatPriceVND(priceBreakdown.totalPrice)}
        </span>
      </div>

      {validationMessage && (
        <p
          className="mb-3 rounded-xl bg-subtle px-3 py-2 text-sm leading-5 text-ink"
          role="alert"
        >
          {validationMessage}
        </p>
      )}

      <button
        type="button"
        onClick={onContinue}
        className="min-h-[52px] w-full rounded-xl border border-brand bg-transparent px-4 py-3 text-sm font-semibold text-ink transition-colors hover:bg-ink hover:text-white focus-visible:ring-2 focus-visible:ring-action/40"
      >
        Xem trước &amp; đặt bánh
      </button>
      <Link
        href="/products"
        className="mt-3 flex min-h-[44px] w-full items-center justify-center text-center text-sm font-medium text-muted underline decoration-line underline-offset-4 transition-colors hover:text-ink hover:decoration-action"
      >
        Chọn bánh không tùy chỉnh
      </Link>
    </aside>
  );
}

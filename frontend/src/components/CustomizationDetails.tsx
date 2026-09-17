import React from "react";
import { CustomizationJson } from "@/types/customization";

interface CustomizationDetailsProps {
  customizationJson: CustomizationJson | Record<string, unknown>;
}

export default function CustomizationDetails({ customizationJson }: CustomizationDetailsProps) {
  if (!customizationJson) return null;
  const json = customizationJson as CustomizationJson;
  const zones = json.zones;

  return (
    <div className="p-4 space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {json.size && (
          <div className="bg-white rounded-lg p-2.5 border border-line">
            <p className="text-xs text-ink font-medium mb-0.5">📏 Kích thước</p>
            <p className="font-bold text-ink text-sm">{json.size}</p>
          </div>
        )}
        {json.flavor && (
          <div className="bg-white rounded-lg p-2.5 border border-line">
            <p className="text-xs text-ink font-medium mb-0.5">🍰 Hương vị</p>
            <p className="font-bold text-ink text-sm">{json.flavor}</p>
          </div>
        )}
        {json.cream_type && (
          <div className="bg-white rounded-lg p-2.5 border border-line">
            <p className="text-xs text-ink font-medium mb-0.5">🧁 Loại kem</p>
            <p className="font-bold text-ink text-sm">{json.cream_type}</p>
          </div>
        )}
        {json.cream_color && (
          <div className="bg-white rounded-lg p-2.5 border border-line">
            <p className="text-xs text-ink font-medium mb-0.5">🎨 Màu kem</p>
            <div className="flex items-center gap-2">
              <span
                className="inline-block w-6 h-6 rounded-full border-2 border-line shadow-sm flex-shrink-0"
                style={{ backgroundColor: json.cream_color }}
              />
              <p className="font-bold text-ink text-sm font-mono">{json.cream_color}</p>
            </div>
          </div>
        )}
      </div>
      {Array.isArray(json.topping_type) && json.topping_type.length > 0 && (
        <div className="bg-white rounded-lg p-2.5 border border-line">
          <p className="text-xs text-ink font-medium mb-1.5">🍓 Topping</p>
          <div className="flex flex-wrap gap-1.5">
            {json.topping_type.map((t: string, i: number) => (
              <span key={i} className="px-2 py-0.5 bg-subtle text-ink rounded-full text-xs font-medium">{t}</span>
            ))}
          </div>
        </div>
      )}
      {zones && typeof zones === "object" && (
        <div className="space-y-2">
          <p className="text-xs text-ink font-medium">🖌️ Trang trí từng vùng bánh</p>
          <div className="grid grid-cols-3 gap-2">
            {(["top", "body", "border"] as const).map((zone) => {
              const z = zones[zone];
              if (!z || (!z.color && !z.decoration && (!Array.isArray(z.toppings) || z.toppings.length === 0))) return null;
              const zoneLabel = { top: "Mặt trên", body: "Thân bánh", border: "Viền" }[zone];
              return (
                <div key={zone} className="bg-white rounded-lg p-2 border border-line text-xs">
                  <p className="font-semibold text-ink mb-1">{zoneLabel}</p>
                  {z.color && typeof z.color === "string" && (
                    <div className="flex items-center gap-1 mb-0.5">
                      <span className="w-3 h-3 rounded-full border border-line" style={{ backgroundColor: z.color }} />
                      <span className="text-muted font-mono">{z.color}</span>
                    </div>
                  )}
                  {z.decoration && typeof z.decoration === "string" && <p className="text-muted">✨ {z.decoration}</p>}
                  {Array.isArray(z.toppings) && z.toppings.length > 0 && (
                    <p className="text-muted">🍓 {z.toppings.join(", ")}</p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
      {json.special_notes && (
        <div className="bg-subtle border-2 border-line rounded-lg p-3">
          <p className="text-xs font-bold text-ink mb-1">⚠️ Ghi chú đặc biệt của khách</p>
          <p className="text-ink font-medium text-sm whitespace-pre-wrap">{json.special_notes}</p>
        </div>
      )}
    </div>
  );
}

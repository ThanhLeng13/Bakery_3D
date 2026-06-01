"use client";

/**
 * Cake Builder page.
 * Integrates CakeSVG, OptionsPanel, SizeSelector, CompletionPanel,
 * PriceDisplay, and PreviewModal for the full customization flow.
 *
 * Validates: Requirements 2.6, 2.7, 2.8
 */

import { useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { type CakeZone } from "@/components/cake-builder/CakeSVG";

const CakeSVG = dynamic(() => import("@/components/cake-builder/CakeSVG"), {
  ssr: false,
});

import OptionsPanel from "@/components/cake-builder/OptionsPanel";
import { SizeSelector } from "@/components/cake-builder/SizeSelector";
import { PriceDisplay } from "@/components/cake-builder/PriceDisplay";
import { CompletionPanel } from "@/components/cake-builder/CompletionPanel";
import { PreviewModal } from "@/components/cake-builder/PreviewModal";
import { useCakeBuilder } from "@/hooks/useCakeBuilder";
import type { ZoneCustomization } from "@/types";

export default function CakeBuilderPage() {
  const router = useRouter();
  const { design, priceBreakdown, actions } = useCakeBuilder({
    size: "20cm",
    cream_color: "#E8837A",
    zones: {
      top: {},
      body: { color: "#E8837A" },
      border: { color: "#D4A574" },
    },
  });

  const [activeZone, setActiveZone] = useState<CakeZone | null>(null);
  const [hoveredZone, setHoveredZone] = useState<CakeZone | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const handleZoneClick = useCallback((zone: CakeZone) => {
    setActiveZone((prev) => (prev === zone ? null : zone));
  }, []);

  const handleZoneHover = useCallback((zone: CakeZone | null) => {
    setHoveredZone(zone);
  }, []);

  const handleOptionSelect = useCallback(
    (zone: CakeZone, option: Partial<ZoneCustomization>) => {
      actions.setZoneCustomization(zone, option);
    },
    [actions]
  );

  const handleClosePanel = useCallback(() => {
    setActiveZone(null);
  }, []);

  const handleComplete = useCallback(() => {
    // Store customization data as JSON in localStorage
    const customizationJson = JSON.stringify(design);
    localStorage.setItem("cake_customization_json", customizationJson);
    // Show preview modal
    setShowPreview(true);
  }, [design]);

  const handleOrder = useCallback(() => {
    // Navigate to checkout with design data stored in localStorage
    router.push("/checkout");
  }, [router]);

  const handleClosePreview = useCallback(() => {
    setShowPreview(false);
  }, []);

  return (
    <main className="min-h-screen bg-cream">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-100 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="font-heading text-lg text-mocha font-bold flex items-center gap-1.5 hover:text-pink-pastel transition-colors min-h-[44px]"
              aria-label="Về trang chủ"
            >
              🎂 <span className="hidden sm:inline">Bơ Nơ</span>
            </Link>
            <span className="text-mocha/20">|</span>
            <h1 className="font-heading text-xl md:text-2xl text-mocha font-bold">
              Thiết kế bánh kem
            </h1>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Instructions */}
        <p className="text-center text-mocha/70 text-sm mb-6">
          Nhấn vào từng vùng trên bánh để tùy chỉnh theo ý muốn
        </p>

        {/* Layout: Cake + Options Panel */}
        <div className="flex flex-col md:flex-row items-start justify-center gap-6">
          {/* Left column: Cake SVG + Size Selector */}
          <div className="w-full md:w-1/2 lg:w-2/5 space-y-6">
            {/* Cake SVG */}
            <div className="flex justify-center">
              <CakeSVG
                design={design}
                activeZone={activeZone}
                hoveredZone={hoveredZone}
                onZoneClick={handleZoneClick}
                onZoneHover={handleZoneHover}
              />
            </div>

            {/* Size Selector */}
            <SizeSelector
              selectedSize={design.size}
              onSizeChange={actions.setSize}
            />

            {/* Price Display */}
            <PriceDisplay priceBreakdown={priceBreakdown} />
          </div>

          {/* Right column: Options Panel or Completion Panel */}
          <div className="hidden md:block md:w-1/2 lg:w-2/5 space-y-6">
            {activeZone && (
              <OptionsPanel
                activeZone={activeZone}
                zoneCustomization={design.zones[activeZone]}
                onOptionSelect={handleOptionSelect}
                onClose={handleClosePanel}
              />
            )}

            {/* Completion Panel */}
            <CompletionPanel
              design={design}
              onFlavorChange={actions.setFlavor}
              onCreamTypeChange={actions.setCreamType}
              onCreamColorChange={actions.setCreamColor}
              onSpecialNotesChange={actions.setSpecialNotes}
              onComplete={handleComplete}
            />
          </div>
        </div>

        {/* Mobile Options Panel (bottom sheet) */}
        <div className="md:hidden">
          <OptionsPanel
            activeZone={activeZone}
            zoneCustomization={activeZone ? design.zones[activeZone] : {}}
            onOptionSelect={handleOptionSelect}
            onClose={handleClosePanel}
          />
        </div>

        {/* Mobile Completion Panel */}
        <div className="md:hidden mt-6">
          <CompletionPanel
            design={design}
            onFlavorChange={actions.setFlavor}
            onCreamTypeChange={actions.setCreamType}
            onCreamColorChange={actions.setCreamColor}
            onSpecialNotesChange={actions.setSpecialNotes}
            onComplete={handleComplete}
          />
        </div>

        {/* Zone legend */}
        <div className="mt-8 flex flex-wrap justify-center gap-4 text-sm text-mocha/60">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-pink-pastel/30 border border-pink-pastel" />
            <span>Mặt trên (Toppings)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-pink-pastel/50 border border-pink-pastel" />
            <span>Thân bánh (Kem & Hoa văn)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-[#D4A574]/50 border border-[#D4A574]" />
            <span>Viền bánh (Trang trí)</span>
          </div>
        </div>
      </div>

      {/* Preview Modal */}
      <PreviewModal
        design={design}
        priceBreakdown={priceBreakdown}
        isOpen={showPreview}
        onClose={handleClosePreview}
        onOrder={handleOrder}
      />
    </main>
  );
}

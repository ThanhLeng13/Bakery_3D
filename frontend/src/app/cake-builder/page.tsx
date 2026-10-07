"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import Header from "@/components/Header";
import ConfiguratorRail, {
  type BuilderStep,
} from "@/components/cake-builder/ConfiguratorRail";
import CakeModelPicker from "@/components/cake-builder/CakeModelPicker";
import OrderSummary from "@/components/cake-builder/OrderSummary";
import { PreviewModal } from "@/components/cake-builder/PreviewModal";
import { type CakeZone } from "@/components/cake-builder/CakeSVG";
import { useCakeBuilder } from "@/hooks/useCakeBuilder";
import type { Cake3DModel, Cake3DModelSlug, ZoneCustomization } from "@/types";
import { apiClient } from "@/lib/api";
import { CAKE_BODY_MODELS, LOCAL_CAKE_3D_MODELS } from "@/lib/cake-body-models";

const Cake3D = dynamic(() => import("@/components/cake-builder/Cake3D"), {
  ssr: false,
  loading: () => (
    <div className="mx-auto flex aspect-square w-full max-w-[760px] items-center justify-center md:aspect-[16/10] 2xl:aspect-[16/9] 2xl:max-w-[1000px]">
      <span className="text-xs font-medium uppercase tracking-[0.16em] text-muted 2xl:text-sm">
        Đang dựng bánh 3D...
      </span>
    </div>
  ),
});

const STEP_HOTSPOTS: Array<{
  id: string;
  step: BuilderStep;
  zone?: CakeZone;
  label: string;
  left: string;
  top: string;
}> = [
  {
    id: "topping",
    step: "top",
    zone: "top",
    label: "Topping",
    left: "38%",
    top: "36%",
  },
  {
    id: "color",
    step: "color",
    zone: "top",
    label: "Màu sắc",
    left: "56%",
    top: "35%",
  },
  {
    id: "body",
    step: "body",
    zone: "body",
    label: "Hoa văn",
    left: "33%",
    top: "54%",
  },
  {
    id: "decoration",
    step: "border",
    zone: "border",
    label: "Trang trí",
    left: "66%",
    top: "52%",
  },
  {
    id: "border",
    step: "border",
    zone: "border",
    label: "Viền bánh",
    left: "56%",
    top: "64%",
  },
];

function isCakeZone(step: BuilderStep): step is CakeZone {
  return step === "top" || step === "body" || step === "border";
}

function CakeBuilderContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedModel = searchParams.get("model");
  const { design, priceBreakdown, actions } = useCakeBuilder({
    size: "20cm",
    cream_color: "#F2F1EE",
    zones: {
      top: {},
      body: { color: "#F2F1EE" },
      border: { color: "#F2F1EE" },
    },
  });

  const [modelLibrary, setModelLibrary] = useState<Cake3DModel[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState(false);
  const [activeStep, setActiveStep] = useState<BuilderStep>("size");
  const [showStepDetail, setShowStepDetail] = useState(false);
  const [activeZone, setActiveZone] = useState<CakeZone | null>(null);
  const [hoveredZone, setHoveredZone] = useState<CakeZone | null>(null);
  const [autoRotate, setAutoRotate] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );
  const configuratorRef = useRef<HTMLDivElement>(null);

  // `?bare=1` ẩn toàn bộ giao diện, chỉ còn canvas. Dùng cho ảnh chụp kiểm tra
  // hình học: đo trên ảnh có nút bấm và chữ thì mọi mẫu đều ra cùng một con
  // số, vì phần lớn vùng đo rơi vào giao diện chứ không phải bánh.
  const bareCapture =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("bare") === "1";

  useEffect(() => {
    if (requestedModel && requestedModel in CAKE_BODY_MODELS) {
      actions.setModelSlug(requestedModel as Cake3DModelSlug);
    }
  }, [actions, requestedModel]);

  useEffect(() => {
    let active = true;
    apiClient
      .get<{ models: Cake3DModel[] }>("/api/v1/cake-3d-models?category=birthday")
      .then((response) => {
        if (!active) return;
        setModelLibrary(response.models);
        setModelsError(false);
      })
      .catch(() => {
        // Static GLBs ship with the frontend, so Cake Studio remains functional
        // while the one-time DB migration/API deployment is pending.
        if (active) {
          setModelLibrary(LOCAL_CAKE_3D_MODELS);
          setModelsError(false);
        }
      })
      .finally(() => {
        if (active) setModelsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleStepChange = useCallback((step: BuilderStep) => {
    setActiveStep(step);
    setActiveZone(isCakeZone(step) ? step : null);
    setShowStepDetail(true);
    setValidationMessage(null);
  }, []);

  const handleZoneClick = useCallback((zone: CakeZone) => {
    setActiveStep(zone);
    setActiveZone(zone);
    setShowStepDetail(true);
    setValidationMessage(null);
  }, []);

  const handleCloseStepDetail = useCallback(() => {
    setShowStepDetail(false);
    setActiveZone(null);
    setHoveredZone(null);
  }, []);

  const handleZoneHover = useCallback((zone: CakeZone | null) => {
    setHoveredZone(zone);
  }, []);

  const showRequiredStep = useCallback(
    (step: BuilderStep, message: string) => {
      handleStepChange(step);
      setValidationMessage(message);

      requestAnimationFrame(() => {
        configuratorRef.current?.scrollIntoView({
          block: "start",
          behavior: "smooth",
        });
        configuratorRef.current?.focus({ preventScroll: true });
      });
    },
    [handleStepChange],
  );

  const handleOptionSelect = useCallback(
    (zone: CakeZone, option: Partial<ZoneCustomization>) => {
      actions.setZoneCustomization(zone, option);
      setValidationMessage(null);
    },
    [actions],
  );

  const handleComplete = useCallback(() => {
    if (!design.flavor) {
      showRequiredStep("flavor", "Vui lòng chọn hương vị trước khi tiếp tục.");
      return;
    }

    if (!design.cream_type) {
      showRequiredStep("cream", "Vui lòng chọn loại kem trước khi tiếp tục.");
      return;
    }

    if (!design.cream_color) {
      showRequiredStep("color", "Vui lòng chọn màu kem trước khi tiếp tục.");
      return;
    }

    localStorage.setItem("cake_customization_json", JSON.stringify(design));
    setValidationMessage(null);
    setShowPreview(true);
  }, [design, showRequiredStep]);

  const handleOrder = useCallback(() => {
    router.push("/checkout");
  }, [router]);

  return (
    <main className="min-h-screen bg-surface text-ink">
      <Header />

      <div className="mx-auto w-full max-w-[660px] px-4 pb-6 pt-5 md:px-0 md:pt-9 lg:max-w-[900px] xl:max-w-[1220px] xl:pt-10 2xl:max-w-[1600px] 2xl:pt-11">
        <div className="mb-5 md:hidden">
          <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-ink">
            Cake studio
          </p>
          <h1 className="mt-1 font-heading text-2xl font-semibold">
            Thiết kế bánh kem 3D
          </h1>
        </div>

        <div className={bareCapture ? "block" : "grid items-start gap-y-8 md:grid-cols-[112px_minmax(360px,1fr)_132px] md:gap-x-[9px] lg:grid-cols-[150px_minmax(480px,1fr)_190px] lg:gap-x-5 xl:grid-cols-[180px_minmax(0,1fr)_230px] xl:gap-x-8 2xl:grid-cols-[220px_minmax(0,1fr)_280px] 2xl:gap-x-10"}>
          <div
            ref={configuratorRef}
            tabIndex={-1}
            className={bareCapture ? "hidden" : "order-2 scroll-mt-24 focus:outline-none md:order-1 md:sticky md:top-[106px] md:max-h-[calc(100vh-116px)] md:overflow-y-auto md:pr-1 xl:top-[126px] xl:max-h-[calc(100vh-142px)]"}
          >
            <CakeModelPicker
              models={modelLibrary}
              selectedSlug={design.model_slug ?? "round-1-tier"}
              loading={modelsLoading}
              error={modelsError}
              onSelect={(modelSlug) => {
                actions.setModelSlug(modelSlug as Cake3DModelSlug);
                setValidationMessage(null);
              }}
            />
            <div className="mt-5">
              <ConfiguratorRail
                design={design}
              activeStep={activeStep}
              activeZone={activeZone}
              detailOpen={showStepDetail}
              onStepChange={handleStepChange}
              onCloseDetail={handleCloseStepDetail}
              onSizeChange={(size) => {
                actions.setSize(size);
                setValidationMessage(null);
              }}
              onFlavorChange={(flavor) => {
                actions.setFlavor(flavor);
                setValidationMessage(null);
              }}
              onCreamTypeChange={(creamType) => {
                actions.setCreamType(creamType);
                setValidationMessage(null);
              }}
              onCreamColorChange={(color) => {
                actions.setCreamColor(color);
                setValidationMessage(null);
              }}
              onSpecialNotesChange={actions.setSpecialNotes}
              onZoneOptionSelect={handleOptionSelect}
              onCloseZone={() => setActiveZone(null)}
              />
            </div>
          </div>

          <section
            className="order-1 min-w-0 md:order-2"
            aria-label="Mô hình bánh kem 3D"
          >
            <h1 className="sr-only">Thiết kế bánh kem 3D</h1>

            <div className="relative">
              <Cake3D
                design={design}
                activeZone={activeZone}
                hoveredZone={hoveredZone}
                onZoneClick={handleZoneClick}
                onZoneHover={handleZoneHover}
                autoRotate={autoRotate}
                enableControls={false}
              />

              {!autoRotate &&
                STEP_HOTSPOTS.map((hotspot) => {
                  const selected =
                    showStepDetail && activeStep === hotspot.step;

                  return (
                    <button
                      key={hotspot.id}
                      type="button"
                      onClick={() => handleStepChange(hotspot.step)}
                      onMouseEnter={() => handleZoneHover(hotspot.zone ?? null)}
                      onMouseLeave={() => handleZoneHover(null)}
                      onFocus={() => handleZoneHover(hotspot.zone ?? null)}
                      onBlur={() => handleZoneHover(null)}
                      aria-label={`Tùy chỉnh ${hotspot.label}`}
                      aria-pressed={selected}
                      className="group absolute z-20 flex h-11 w-11 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-0 bg-transparent shadow-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
                      style={{ left: hotspot.left, top: hotspot.top }}
                    >
                      <span
                        className={`h-2.5 w-2.5 rounded-full border shadow-sm transition-colors xl:h-3 xl:w-3 ${
                          selected
                            ? "border-white bg-action"
                            : "border-brand/50 bg-white/80 group-hover:border-ink group-hover:bg-white"
                        }`}
                        aria-hidden="true"
                      />
                      <span className="pointer-events-none absolute left-1/2 top-[calc(100%+8px)] -translate-x-1/2 whitespace-nowrap rounded-full bg-ink px-2.5 py-1 text-[10px] font-semibold text-white opacity-0 shadow-md transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
                        {hotspot.label}
                      </span>
                    </button>
                  );
                })}
            </div>

            <div className="flex items-center justify-center">
              <button
                type="button"
                onClick={() => setAutoRotate((current) => !current)}
                aria-pressed={autoRotate}
                aria-label={`Tự động xoay bánh: ${autoRotate ? "Bật" : "Tắt"}`}
                className="flex min-h-[36px] items-center gap-1.5 rounded-full px-2 text-[9px] font-medium uppercase tracking-[0.08em] text-muted transition-colors hover:text-ink xl:min-h-[44px] xl:text-[11px] 2xl:min-h-[48px] 2xl:text-xs"
              >
                <span
                  className={`relative h-4 w-7 rounded-full transition-colors ${
                    autoRotate ? "bg-action" : "bg-ink/20"
                  }`}
                  aria-hidden="true"
                >
                  <span
                    className={`absolute top-0.5 h-3 w-3 rounded-full bg-white shadow-sm transition-transform ${
                      autoRotate ? "translate-x-3.5" : "translate-x-0.5"
                    }`}
                  />
                </span>
                {/* Visible label names the feature; the switch state follows it,
                    so sighted users get the same context screen readers do. */}
                <span aria-hidden="true">Tự động xoay</span>
                <span aria-hidden="true">{autoRotate ? "Bật" : "Tắt"}</span>
              </button>
            </div>
          </section>

          <div className={bareCapture ? "hidden" : "order-3 md:sticky md:top-[106px] xl:top-[126px]"}>
            <OrderSummary
              design={design}
              priceBreakdown={priceBreakdown}
              validationMessage={validationMessage}
              onContinue={handleComplete}
            />
          </div>
        </div>

        <footer className="hidden md:block" aria-label="Liên kết cuối trang">
          <div
            className="mt-3 flex justify-center gap-3 xl:mt-5 xl:gap-4 2xl:mt-6 2xl:gap-5"
            aria-label="Mạng xã hội"
          >
            {[
              { label: "Facebook", text: "f" },
              { label: "Instagram", text: "◎" },
              { label: "Pinterest", text: "p" },
            ].map((item) => (
              <span
                key={item.label}
                role="img"
                aria-label={item.label}
                className="flex h-8 w-8 items-center justify-center border border-line text-[11px] font-semibold text-ink xl:h-10 xl:w-10 xl:text-sm 2xl:h-12 2xl:w-12 2xl:text-base"
              >
                {item.text}
              </span>
            ))}
          </div>

          <div className="mx-auto mt-5 grid w-[360px] grid-cols-3 gap-8 text-center text-[7px] leading-4 text-muted xl:mt-7 xl:w-[520px] xl:text-[10px] xl:leading-5 2xl:mt-8 2xl:w-[600px] 2xl:text-[11px] 2xl:leading-6">
            <div>
              <p className="mb-1 text-[8px] font-bold uppercase tracking-[0.14em] text-ink xl:text-[11px] 2xl:text-xs">
                Bơ Nơ
              </p>
              <Link href="/" className="block hover:text-ink">
                Trang chủ
              </Link>
              <Link href="/auth/login" className="block hover:text-ink">
                Đăng nhập
              </Link>
            </div>
            <div>
              <p className="mb-1 text-[8px] font-bold uppercase tracking-[0.14em] text-ink xl:text-[11px] 2xl:text-xs">
                Sản phẩm
              </p>
              <Link href="/products" className="block hover:text-ink">
                Danh mục bánh
              </Link>
              <Link
                href="/cake-builder"
                className="block hover:text-ink"
              >
                Thiết kế 3D
              </Link>
            </div>
            <div>
              <p className="mb-1 text-[8px] font-bold uppercase tracking-[0.14em] text-ink xl:text-[11px] 2xl:text-xs">
                Tài khoản
              </p>
              <Link href="/orders" className="block hover:text-ink">
                Đơn hàng
              </Link>
              <Link href="/loyalty" className="block hover:text-ink">
                Tích điểm
              </Link>
            </div>
          </div>
          <p className="mt-4 text-center text-[6px] text-muted xl:mt-6 xl:text-[9px] 2xl:mt-7 2xl:text-[10px]">
            © 2026 Bơ Nơ Bakery. All rights reserved.
          </p>
        </footer>
      </div>

      <PreviewModal
        design={design}
        priceBreakdown={priceBreakdown}
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        onOrder={handleOrder}
      />
    </main>
  );
}

export default function CakeBuilderPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-surface text-ink">
          <Header />
          <div className="mx-auto flex min-h-[60vh] max-w-5xl items-center justify-center px-4">
            <span className="text-xs font-medium uppercase tracking-[0.16em] text-muted">Đang mở Cake Studio...</span>
          </div>
        </main>
      }
    >
      <CakeBuilderContent />
    </Suspense>
  );
}

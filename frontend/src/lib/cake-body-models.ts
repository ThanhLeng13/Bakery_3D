import type { Cake3DModel, Cake3DModelSlug, CakeSize } from "@/types";

export type CakeBodyShape = "round" | "square" | "heart";

export interface CakeBodyModelDefinition {
  slug: Cake3DModelSlug;
  glbUrl: string;
  shape: CakeBodyShape;
  tiers: 1 | 2 | 3;
  /** Models whose published sizes/pricing are currently supported by checkout. */
  allowedSizes: CakeSize[];
  /** Preview-only models are intentionally not offered for new custom orders yet. */
  orderable: boolean;
  /** Current border/body decorators assume a radial silhouette. */
  supportsRadialDecorations: boolean;
}

/**
 * The fallback registry is intentionally kept beside the remote warehouse API.
 * It lets the builder remain useful before the SQL migration has been run, while
 * the API remains the source of truth for visible model names and activation.
 */
export const CAKE_BODY_MODELS: Record<Cake3DModelSlug, CakeBodyModelDefinition> = {
  "round-1-tier": {
    slug: "round-1-tier",
    glbUrl: "/models/cake-tron-1-tang.glb",
    shape: "round",
    tiers: 1,
    allowedSizes: ["16cm", "20cm", "24cm"],
    orderable: true,
    supportsRadialDecorations: true,
  },
  "round-2-tier": {
    slug: "round-2-tier",
    glbUrl: "/models/cake-tron-2-tang.glb",
    shape: "round",
    tiers: 2,
    allowedSizes: ["2-tier"],
    orderable: true,
    supportsRadialDecorations: true,
  },
  "round-3-tier": {
    slug: "round-3-tier",
    glbUrl: "/models/cake-tron-3-tang.glb",
    shape: "round",
    tiers: 3,
    allowedSizes: [],
    orderable: false,
    supportsRadialDecorations: true,
  },
  "square-1-tier": {
    slug: "square-1-tier",
    glbUrl: "/models/cake-vuong-1-tang.glb",
    shape: "square",
    tiers: 1,
    allowedSizes: ["16cm", "20cm", "24cm"],
    orderable: false,
    supportsRadialDecorations: false,
  },
  "heart-1-tier": {
    slug: "heart-1-tier",
    glbUrl: "/models/cake-trai-tim.glb",
    shape: "heart",
    tiers: 1,
    allowedSizes: ["16cm", "20cm", "24cm"],
    orderable: false,
    supportsRadialDecorations: false,
  },
  "tall-1-tier": {
    slug: "tall-1-tier",
    glbUrl: "/models/cake-cao-1-tang.glb",
    shape: "round",
    tiers: 1,
    allowedSizes: ["16cm", "20cm", "24cm"],
    orderable: false,
    supportsRadialDecorations: true,
  },
};

export function getCakeBodyModel(slug?: Cake3DModelSlug): CakeBodyModelDefinition {
  // Slug đến từ API/CSDL nên về mặt kiểu có thể là giá trị chưa có trong registry
  // (ví dụ admin thêm mẫu mới trong DB). Thiếu fallback thì `definition.glbUrl`
  // và `definition.orderable` sẽ nổ ngay trên giao diện.
  return CAKE_BODY_MODELS[slug as Cake3DModelSlug] ?? CAKE_BODY_MODELS["round-1-tier"];
}

/** Allows Cake Studio to work before the one-time Supabase SQL migration runs. */
export const LOCAL_CAKE_3D_MODELS: Cake3DModel[] = Object.values(CAKE_BODY_MODELS).map((model) => ({
  id: model.slug,
  slug: model.slug,
  name: {
    "round-1-tier": "Bánh tròn 1 tầng",
    "round-2-tier": "Bánh tròn 2 tầng",
    "round-3-tier": "Bánh tròn 3 tầng",
    "square-1-tier": "Bánh vuông 1 tầng",
    "heart-1-tier": "Bánh trái tim 1 tầng",
    "tall-1-tier": "Bánh cao 1 tầng",
  }[model.slug],
  glb_url: model.glbUrl,
  thumbnail_url: null,
  tags: [model.shape, `${model.tiers}-tier`],
  category: "birthday",
  created_at: "2026-09-24T00:00:00.000Z",
}));

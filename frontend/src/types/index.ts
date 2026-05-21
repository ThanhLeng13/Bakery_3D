/**
 * Core type definitions for Cake Shop AI Web
 */

export type UserRole = "customer" | "admin" | "baker";

export type OrderStatus =
  | "pending"
  | "confirmed"
  | "in_production"
  | "ready"
  | "delivered";

export type CakeSize = "16cm" | "20cm" | "24cm" | "2-tier";

export type ProductCategory = "bánh âu" | "bánh ngọt";

export interface ZoneCustomization {
  color?: string;
  decoration?: string;
  topping?: string;
}

export interface CakeDesign {
  size: CakeSize;
  flavor: string;
  cream_type: string;
  cream_color: string;
  topping_type?: string;
  special_notes?: string;
  zones: {
    top: ZoneCustomization;
    body: ZoneCustomization;
    border: ZoneCustomization;
  };
}

export interface PriceBreakdown {
  basePrice: number;
  toppingCost: number;
  decorationCost: number;
  totalPrice: number;
}

// Product catalog types

export interface ProductImage {
  id: string;
  url: string;
  sort_order: number;
}

export interface ProductListItem {
  id: string;
  name: string;
  description: string | null;
  category: string;
  base_price: number;
  image_url: string | null;
  average_rating: number | null;
  review_count: number;
  created_at: string;
}

export interface ProductSize {
  name: string;
  price: number;
}

export interface ProductFlavor {
  name: string;
  additional_cost: number;
}

export interface ProductDetailResponse {
  id: string;
  name: string;
  description: string | null;
  category: string;
  base_price: number;
  sizes: ProductSize[];
  flavors: ProductFlavor[];
  is_active: boolean;
  images: ProductImage[];
  average_rating: number | null;
  review_count: number;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ProductListResponse {
  products: ProductListItem[];
  pagination: PaginationMeta;
}

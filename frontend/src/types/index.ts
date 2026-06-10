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

export type ProductType = "sweet" | "cake";
// sweet = bánh ngọt (có tồn kho, mua trực tiếp)
// cake  = bánh kem  (đặt hàng theo yêu cầu)

// Branch types
export interface Branch {
  id: string;
  name: string;
  address: string | null;
  phone: string | null;
}

export interface BranchStock {
  branch_id: string | null;
  branch_name: string;
  branch_address: string | null;
  quantity_available: number;
  expires_soonest: string | null;
}

export interface StockByBranchResponse {
  product_id: string;
  total_available: number;
  branches: BranchStock[];
}

export type CakeSize = "16cm" | "20cm" | "24cm" | "2-tier";

export type ProductCategory = "bánh âu" | "bánh ngọt";

export interface ZoneCustomization {
  color?: string;
  decoration?: string;
  /** Danh sách toppings được chọn (hỗ trợ nhiều topping cùng lúc) */
  toppings?: string[];
  /** Set true when user explicitly customizes this zone's color via OptionsPanel.
   *  Prevents setCreamColor from overwriting the user's choice. */
  customized?: boolean;
}

export interface CakeDesign {
  size: CakeSize;
  flavor: string;
  cream_type: string;
  cream_color: string;
  topping_type?: string[];
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
  product_type: "sweet" | "cake";
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
  product_type: "sweet" | "cake";
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

// Cart types (chỉ dùng cho bánh ngọt)

export interface CartItem {
  /** Unique key: productId */
  cartKey: string;
  productId: string;
  productName: string;
  imageUrl: string | null;
  unitPrice: number;
  quantity: number;
  /** Ngày hết hạn gần nhất của lô hàng (bánh ngọt) */
  expiresAt: string | null;
  /** Chi nhánh mua hàng */
  branchId: string | null;
  /** Tên chi nhánh để hiển thị */
  branchName: string | null;
}

export interface CartState {
  items: CartItem[];
  totalItems: number;
  totalPrice: number;
}

// Inventory types

export interface ProductBatch {
  id: string;
  quantity_available: number;
  produced_at: string;
  expires_at: string;
}

export interface StockInfo {
  product_id: string;
  total_available: number;
  expires_soonest: string | null;
  batches: ProductBatch[];
}

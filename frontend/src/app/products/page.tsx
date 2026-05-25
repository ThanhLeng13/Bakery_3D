import { Metadata } from "next";
import ProductCatalogClient from "@/components/ProductCatalogClient";
import { ProductListResponse } from "@/types";
import Header from "@/components/Header";
export const revalidate = 60; // ISR cache TTL 60 seconds

export const metadata: Metadata = {
  title: "Danh Mục Bánh Kem | La Douceur",
  description: "Khám phá bộ sưu tập bánh kem thủ công của chúng tôi. Nhiều hương vị đặc sắc, chất lượng thượng hạng.",
};

interface PageProps {
  searchParams: {
    page?: string;
    category?: string;
  };
}
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getProducts(page: number, category: string): Promise<ProductListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: "20",
  });
  if (category && category !== "all") {
    params.set("category", category);
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/products?${params.toString()}`, {
    next: { revalidate: 60, tags: ["products"] },
  });

  if (!res.ok) {
    throw new Error("Không thể tải danh mục sản phẩm.");
  }

  return res.json();
}

export default async function ProductCatalogPage({ searchParams }: PageProps) {
  const page = parseInt(searchParams.page || "1", 10);
  const category = searchParams.category || "all";

  try {
    const data = await getProducts(page, category);
    return (
      <>
        <Header />
        <ProductCatalogClient
          initialProducts={data.products}
          initialTotalPages={data.pagination.total_pages}
          currentPage={page}
          currentCategory={category}
        />
      </>
    );
  } catch {
    return (
      <>
        <Header />
        <main className="min-h-screen bg-cream flex items-center justify-center">
          <div className="text-center px-4">
            <p className="text-mocha/70 text-lg mb-4">
              Không thể tải danh mục sản phẩm. Vui lòng thử lại sau.
            </p>
          </div>
        </main>
      </>
    );
  }
}

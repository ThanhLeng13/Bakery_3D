import { Metadata } from "next";
import ProductDetailClient from "@/components/ProductDetailClient";
import { ProductDetailResponse } from "@/types";
import Header from "@/components/Header";

export const revalidate = 60; // ISR cache TTL 60 seconds

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function getProduct(id: string): Promise<ProductDetailResponse | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/products/${id}`, {
      next: { revalidate: 60, tags: [`product-${id}`] },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const product = await getProduct(params.id);
  if (!product) {
    return {
      title: "Không tìm thấy sản phẩm | La Douceur",
      description: "Sản phẩm không tồn tại hoặc đã ngừng kinh doanh.",
    };
  }

  const description = product.description || `Chi tiết sản phẩm ${product.name} tại tiệm bánh La Douceur.`;
  const image = product.images.length > 0 ? product.images[0].url : "";

  return {
    title: `${product.name} | La Douceur`,
    description,
    openGraph: {
      title: `${product.name} | La Douceur`,
      description,
      images: image ? [{ url: image }] : [],
    },
  };
}

export default async function ProductDetailPage({ params }: { params: { id: string } }) {
  const product = await getProduct(params.id);

  if (!product) {
    return (
      <main className="min-h-screen bg-cream flex items-center justify-center">
        <div className="text-center px-4">
          <p className="text-mocha/70 text-lg mb-4">Không tìm thấy sản phẩm.</p>
          <a
            href="/products"
            className="inline-block px-6 py-2 bg-pink-pastel text-white rounded-full hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
          >
            Quay lại danh mục
          </a>
        </div>
      </main>
    );
  }

  return (
    <>
      <Header />
      <ProductDetailClient product={product} />
    </>
  );
}

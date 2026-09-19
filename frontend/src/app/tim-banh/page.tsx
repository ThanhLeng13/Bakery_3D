import { Metadata } from "next";
import Header from "@/components/Header";
import ImageSearchClient from "@/components/ImageSearchClient";

export const metadata: Metadata = {
  title: "Tìm bánh bằng hình ảnh | Bơ Nơ",
  description:
    "Tải lên ảnh chiếc bánh bạn yêu thích, chúng tôi dùng AI thị giác để tìm những mẫu bánh giống nhất trong tiệm.",
};

export default function ImageSearchPage() {
  return (
    <>
      <Header />
      <ImageSearchClient />
    </>
  );
}

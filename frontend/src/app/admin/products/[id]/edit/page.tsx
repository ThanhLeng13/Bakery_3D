"use client";

/**
 * Edit product form page (same as create, pre-filled with existing data).
 * Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
 */

import { useState, useEffect, useRef } from "react";
import { useRouter, useParams } from "next/navigation";
import { apiClient } from "@/lib/api";
import { getStoredToken } from "@/lib/auth";

interface SizeOption {
  name: string;
  price: string;
}

interface FormData {
  name: string;
  description: string;
  category: string;
  base_price: string;
  sizes: SizeOption[];
  flavors: string[];
  is_active: boolean;
}

interface FieldErrors {
  [key: string]: string;
}

interface ImageFile {
  file: File;
  preview: string;
}

interface ExistingImage {
  id: string;
  url: string;
  sort_order: number;
}

interface ProductResponse {
  id: string;
  name: string;
  description: string | null;
  category: string;
  base_price: number;
  sizes: Array<{ name: string; price: number }>;
  flavors: string[];
  is_active: boolean;
  images: ExistingImage[];
  created_at: string;
  updated_at: string;
}

const CATEGORIES = [
  "bánh âu",
  "bánh ngọt",
  "bánh kem",
  "bánh sinh nhật",
  "bánh cưới",
];

const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_IMAGE_SIZE = 5 * 1024 * 1024; // 5MB

export default function AdminProductEditPage() {
  const router = useRouter();
  const params = useParams();
  const productId = params.id as string;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [newImages, setNewImages] = useState<ImageFile[]>([]);
  const [existingImages, setExistingImages] = useState<ExistingImage[]>([]);
  const [imageError, setImageError] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formData, setFormData] = useState<FormData>({
    name: "",
    description: "",
    category: "",
    base_price: "",
    sizes: [{ name: "", price: "" }],
    flavors: [""],
    is_active: true,
  });

  const formatPriceDisplay = (price: number): string => {
    return new Intl.NumberFormat("vi-VN").format(price);
  };

  // Fetch product data
  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const product = await apiClient.get<ProductResponse>(
          `/api/v1/admin/products/${productId}`
        );
        setFormData({
          name: product.name,
          description: product.description || "",
          category: product.category,
          base_price: formatPriceDisplay(product.base_price),
          sizes: product.sizes.map((s) => ({
            name: s.name,
            price: formatPriceDisplay(s.price),
          })),
          flavors: product.flavors.length > 0 ? product.flavors : [""],
          is_active: product.is_active,
        });
        setExistingImages(product.images);
      } catch {
        router.push("/admin/products");
      } finally {
        setLoading(false);
      }
    };
    fetchProduct();
  }, [productId, router]);

  const updateField = (field: keyof FormData, value: unknown) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[field];
        return next;
      });
    }
  };

  const validate = (): boolean => {
    const newErrors: FieldErrors = {};

    if (!formData.name.trim()) {
      newErrors.name = "Tên sản phẩm là bắt buộc";
    } else if (formData.name.trim().length > 200) {
      newErrors.name = "Tên sản phẩm tối đa 200 ký tự";
    }

    if (!formData.description.trim()) {
      newErrors.description = "Mô tả sản phẩm là bắt buộc";
    } else if (formData.description.trim().length > 2000) {
      newErrors.description = "Mô tả tối đa 2000 ký tự";
    }

    if (!formData.category) {
      newErrors.category = "Vui lòng chọn danh mục";
    }

    const price = parseInt(formData.base_price.replace(/[.,\s]/g, ""), 10);
    if (!formData.base_price.trim() || isNaN(price)) {
      newErrors.base_price = "Giá cơ bản là bắt buộc";
    } else if (price < 1000) {
      newErrors.base_price = "Giá tối thiểu 1.000₫";
    } else if (price > 999999999) {
      newErrors.base_price = "Giá tối đa 999.999.999₫";
    }

    const validSizes = formData.sizes.filter(
      (s) => s.name.trim() || s.price.trim()
    );
    if (validSizes.length === 0) {
      newErrors.sizes = "Cần ít nhất 1 tùy chọn kích thước";
    } else if (validSizes.length > 10) {
      newErrors.sizes = "Tối đa 10 tùy chọn kích thước";
    } else {
      for (let i = 0; i < validSizes.length; i++) {
        if (!validSizes[i].name.trim()) {
          newErrors[`sizes_${i}_name`] = "Tên kích thước là bắt buộc";
        }
        const sizePrice = parseInt(
          validSizes[i].price.replace(/[.,\s]/g, ""),
          10
        );
        if (!validSizes[i].price.trim() || isNaN(sizePrice)) {
          newErrors[`sizes_${i}_price`] = "Giá là bắt buộc";
        } else if (sizePrice < 1000 || sizePrice > 999999999) {
          newErrors[`sizes_${i}_price`] = "Giá từ 1.000 đến 999.999.999₫";
        }
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleImageFiles = (files: FileList | File[]) => {
    setImageError("");
    const fileArray = Array.from(files);

    for (const file of fileArray) {
      if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
        setImageError("Chỉ chấp nhận file JPEG, PNG hoặc WebP");
        return;
      }
      if (file.size > MAX_IMAGE_SIZE) {
        setImageError("Kích thước file tối đa 5MB");
        return;
      }
    }

    const totalImages = existingImages.length + newImages.length + fileArray.length;
    if (totalImages > 10) {
      setImageError("Tối đa 10 hình ảnh");
      return;
    }

    const newFiles: ImageFile[] = fileArray.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
    }));
    setNewImages((prev) => [...prev, ...newFiles]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length > 0) {
      handleImageFiles(e.dataTransfer.files);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const removeNewImage = (index: number) => {
    setNewImages((prev) => {
      const updated = [...prev];
      URL.revokeObjectURL(updated[index].preview);
      updated.splice(index, 1);
      return updated;
    });
  };

  const removeExistingImage = (index: number) => {
    setExistingImages((prev) => prev.filter((_, i) => i !== index));
  };

  const addSize = () => {
    if (formData.sizes.length < 10) {
      setFormData((prev) => ({
        ...prev,
        sizes: [...prev.sizes, { name: "", price: "" }],
      }));
    }
  };

  const removeSize = (index: number) => {
    if (formData.sizes.length > 1) {
      setFormData((prev) => ({
        ...prev,
        sizes: prev.sizes.filter((_, i) => i !== index),
      }));
    }
  };

  const updateSize = (index: number, field: keyof SizeOption, value: string) => {
    setFormData((prev) => ({
      ...prev,
      sizes: prev.sizes.map((s, i) =>
        i === index ? { ...s, [field]: value } : s
      ),
    }));
    const errorKey = `sizes_${index}_${field}`;
    if (errors[errorKey]) {
      setErrors((prev) => {
        const next = { ...prev };
        delete next[errorKey];
        return next;
      });
    }
  };

  const addFlavor = () => {
    setFormData((prev) => ({
      ...prev,
      flavors: [...prev.flavors, ""],
    }));
  };

  const removeFlavor = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      flavors: prev.flavors.filter((_, i) => i !== index),
    }));
  };

  const updateFlavor = (index: number, value: string) => {
    setFormData((prev) => ({
      ...prev,
      flavors: prev.flavors.map((f, i) => (i === index ? value : f)),
    }));
  };

  const formatPriceInput = (value: string): string => {
    const digits = value.replace(/\D/g, "");
    if (!digits) return "";
    return new Intl.NumberFormat("vi-VN").format(parseInt(digits, 10));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    try {
      const validSizes = formData.sizes
        .filter((s) => s.name.trim() && s.price.trim())
        .map((s) => ({
          name: s.name.trim(),
          price: parseInt(s.price.replace(/[.,\s]/g, ""), 10),
        }));

      const validFlavors = formData.flavors.filter((f) => f.trim());

      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        category: formData.category,
        base_price: parseInt(formData.base_price.replace(/[.,\s]/g, ""), 10),
        sizes: validSizes,
        flavors: validFlavors,
        is_active: formData.is_active,
      };

      await apiClient.put(`/api/v1/admin/products/${productId}`, payload);

      // Upload new images if any
      if (newImages.length > 0) {
        for (const img of newImages) {
          const formDataUpload = new FormData();
          formDataUpload.append("file", img.file);

          const token = getStoredToken();
          await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/admin/products/${productId}/images`,
            {
              method: "POST",
              headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
              },
              body: formDataUpload,
            }
          );
        }
      }

      router.push("/admin/products");
    } catch (err: unknown) {
      const apiErr = err as { detail?: string | Array<{ field: string; message: string }> };
      if (apiErr.detail && Array.isArray(apiErr.detail)) {
        const fieldErrors: FieldErrors = {};
        for (const e of apiErr.detail) {
          fieldErrors[e.field] = e.message;
        }
        setErrors(fieldErrors);
      } else if (apiErr.detail && typeof apiErr.detail === "string") {
        setErrors({ _form: apiErr.detail });
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto space-y-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-mocha/5 rounded w-1/3" />
          <div className="h-64 bg-mocha/5 rounded-xl" />
          <div className="h-48 bg-mocha/5 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="text-sm text-mocha/60 hover:text-mocha font-body mb-2 inline-flex items-center gap-1"
        >
          ← Quay lại
        </button>
        <h1 className="font-heading text-2xl text-mocha font-bold">
          Chỉnh sửa sản phẩm
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* General error */}
        {errors._form && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600 font-body">{errors._form}</p>
          </div>
        )}

        {/* Basic info */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-mocha/5 space-y-4">
          <h2 className="font-heading text-lg text-mocha font-semibold">
            Thông tin cơ bản
          </h2>

          {/* Name */}
          <div>
            <label className="block text-sm font-body text-mocha/80 mb-1.5">
              Tên sản phẩm <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => updateField("name", e.target.value)}
              maxLength={200}
              className={`w-full px-4 py-2.5 rounded-lg border font-body text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 ${
                errors.name ? "border-red-300 bg-red-50/50" : "border-mocha/10 bg-cream/30"
              }`}
            />
            {errors.name && (
              <p className="mt-1 text-xs text-red-500 font-body">{errors.name}</p>
            )}
            <p className="mt-1 text-xs text-mocha/40 font-body">{formData.name.length}/200</p>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-body text-mocha/80 mb-1.5">
              Mô tả <span className="text-red-500">*</span>
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => updateField("description", e.target.value)}
              maxLength={2000}
              rows={4}
              className={`w-full px-4 py-2.5 rounded-lg border font-body text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 resize-none ${
                errors.description ? "border-red-300 bg-red-50/50" : "border-mocha/10 bg-cream/30"
              }`}
            />
            {errors.description && (
              <p className="mt-1 text-xs text-red-500 font-body">{errors.description}</p>
            )}
            <p className="mt-1 text-xs text-mocha/40 font-body">{formData.description.length}/2000</p>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-body text-mocha/80 mb-1.5">
              Danh mục <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.category}
              onChange={(e) => updateField("category", e.target.value)}
              className={`w-full px-4 py-2.5 rounded-lg border font-body text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 ${
                errors.category ? "border-red-300 bg-red-50/50" : "border-mocha/10 bg-cream/30"
              }`}
            >
              <option value="">Chọn danh mục</option>
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat.charAt(0).toUpperCase() + cat.slice(1)}
                </option>
              ))}
            </select>
            {errors.category && (
              <p className="mt-1 text-xs text-red-500 font-body">{errors.category}</p>
            )}
          </div>

          {/* Base price */}
          <div>
            <label className="block text-sm font-body text-mocha/80 mb-1.5">
              Giá cơ bản (VND) <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={formData.base_price}
                onChange={(e) => updateField("base_price", formatPriceInput(e.target.value))}
                className={`w-full px-4 py-2.5 pr-10 rounded-lg border font-body text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 ${
                  errors.base_price ? "border-red-300 bg-red-50/50" : "border-mocha/10 bg-cream/30"
                }`}
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-mocha/40">₫</span>
            </div>
            {errors.base_price && (
              <p className="mt-1 text-xs text-red-500 font-body">{errors.base_price}</p>
            )}
          </div>
        </div>

        {/* Sizes */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-mocha/5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-lg text-mocha font-semibold">
              Kích thước <span className="text-red-500">*</span>
            </h2>
            <button
              type="button"
              onClick={addSize}
              disabled={formData.sizes.length >= 10}
              className="text-sm text-pink-pastel hover:text-pink-pastel/80 font-body disabled:opacity-30 disabled:cursor-not-allowed"
            >
              + Thêm kích thước
            </button>
          </div>
          {errors.sizes && (
            <p className="text-xs text-red-500 font-body">{errors.sizes}</p>
          )}
          <div className="space-y-3">
            {formData.sizes.map((size, index) => (
              <div key={index} className="flex items-start gap-3">
                <div className="flex-1">
                  <input
                    type="text"
                    value={size.name}
                    onChange={(e) => updateSize(index, "name", e.target.value)}
                    placeholder="VD: 16cm"
                    className={`w-full px-3 py-2 rounded-lg border font-body text-sm text-mocha placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 ${
                      errors[`sizes_${index}_name`] ? "border-red-300 bg-red-50/50" : "border-mocha/10 bg-cream/30"
                    }`}
                  />
                  {errors[`sizes_${index}_name`] && (
                    <p className="mt-1 text-xs text-red-500 font-body">{errors[`sizes_${index}_name`]}</p>
                  )}
                </div>
                <div className="flex-1">
                  <input
                    type="text"
                    value={size.price}
                    onChange={(e) => updateSize(index, "price", formatPriceInput(e.target.value))}
                    placeholder="Giá (VND)"
                    className={`w-full px-3 py-2 rounded-lg border font-body text-sm text-mocha placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 ${
                      errors[`sizes_${index}_price`] ? "border-red-300 bg-red-50/50" : "border-mocha/10 bg-cream/30"
                    }`}
                  />
                  {errors[`sizes_${index}_price`] && (
                    <p className="mt-1 text-xs text-red-500 font-body">{errors[`sizes_${index}_price`]}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => removeSize(index)}
                  disabled={formData.sizes.length <= 1}
                  className="mt-1 p-2 text-mocha/40 hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  aria-label="Xóa kích thước"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
          <p className="text-xs text-mocha/40 font-body">{formData.sizes.length}/10 kích thước</p>
        </div>

        {/* Flavors */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-mocha/5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-lg text-mocha font-semibold">
              Hương vị
            </h2>
            <button
              type="button"
              onClick={addFlavor}
              className="text-sm text-pink-pastel hover:text-pink-pastel/80 font-body"
            >
              + Thêm hương vị
            </button>
          </div>
          <div className="space-y-3">
            {formData.flavors.map((flavor, index) => (
              <div key={index} className="flex items-center gap-3">
                <input
                  type="text"
                  value={flavor}
                  onChange={(e) => updateFlavor(index, e.target.value)}
                  placeholder="VD: Socola, Vanilla, Matcha..."
                  className="flex-1 px-3 py-2 rounded-lg border border-mocha/10 bg-cream/30 font-body text-sm text-mocha placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-pink-pastel/30"
                />
                <button
                  type="button"
                  onClick={() => removeFlavor(index)}
                  className="p-2 text-mocha/40 hover:text-red-500 transition-colors"
                  aria-label="Xóa hương vị"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Image upload */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-mocha/5 space-y-4">
          <h2 className="font-heading text-lg text-mocha font-semibold">
            Hình ảnh
          </h2>

          {/* Existing images */}
          {existingImages.length > 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
              {existingImages.map((img, index) => (
                <div key={img.id} className="relative group aspect-square">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.url}
                    alt={`Product image ${index + 1}`}
                    className="w-full h-full object-cover rounded-lg"
                  />
                  <button
                    type="button"
                    onClick={() => removeExistingImage(index)}
                    className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Xóa ảnh"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* New image previews */}
          {newImages.length > 0 && (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-3">
              {newImages.map((img, index) => (
                <div key={index} className="relative group aspect-square">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.preview}
                    alt={`New image ${index + 1}`}
                    className="w-full h-full object-cover rounded-lg border-2 border-dashed border-pink-pastel/30"
                  />
                  <button
                    type="button"
                    onClick={() => removeNewImage(index)}
                    className="absolute top-1 right-1 w-6 h-6 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    aria-label="Xóa ảnh mới"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Drop zone */}
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              dragOver
                ? "border-pink-pastel bg-pink-pastel/5"
                : "border-mocha/15 hover:border-pink-pastel/50 hover:bg-cream/50"
            }`}
          >
            <div className="space-y-2">
              <p className="text-3xl">📷</p>
              <p className="font-body text-sm text-mocha/70">
                Kéo thả hình ảnh vào đây hoặc{" "}
                <span className="text-pink-pastel font-medium">nhấn để chọn</span>
              </p>
              <p className="font-body text-xs text-mocha/40">
                JPEG, PNG, WebP · Tối đa 5MB · Tối đa 10 ảnh
              </p>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(e) => {
              if (e.target.files) handleImageFiles(e.target.files);
              e.target.value = "";
            }}
            className="hidden"
          />

          {imageError && (
            <p className="text-xs text-red-500 font-body">{imageError}</p>
          )}
        </div>

        {/* Active status */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-mocha/5">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-heading text-lg text-mocha font-semibold">
                Trạng thái
              </h2>
              <p className="text-sm text-mocha/60 font-body mt-0.5">
                {formData.is_active
                  ? "Sản phẩm đang hiển thị trên trang khách hàng"
                  : "Sản phẩm đang bị ẩn khỏi trang khách hàng"}
              </p>
            </div>
            <button
              type="button"
              onClick={() => updateField("is_active", !formData.is_active)}
              className="relative inline-flex h-7 w-12 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-pink-pastel/30"
              style={{
                backgroundColor: formData.is_active ? "#E8837A" : "#d1d5db",
              }}
              aria-label="Bật/tắt trạng thái hoạt động"
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform shadow-sm ${
                  formData.is_active ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </div>

        {/* Submit */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={() => router.back()}
            className="px-5 py-2.5 rounded-lg font-body text-sm text-mocha/70 hover:bg-white border border-mocha/10 transition-colors"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-6 py-2.5 bg-pink-pastel text-white font-body text-sm font-medium rounded-lg hover:bg-pink-pastel/90 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? "Đang lưu..." : "Lưu thay đổi"}
          </button>
        </div>
      </form>
    </div>
  );
}

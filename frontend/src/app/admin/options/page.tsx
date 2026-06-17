"use client";

/**
 * Admin - Quản lý Thuộc tính bánh (Cake Options)
 * Protected route - requires Admin role (handled by admin layout).
 *
 * 4 tabs: Kích thước | Vị bánh | Topping | Màu sắc
 * CRUD: Thêm / Sửa / Xóa / Ẩn-Hiện options
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { apiClient, ApiError } from "@/lib/api";

type OptionType = "size" | "flavor" | "topping" | "color";

interface CakeOption {
  id: string;
  type: OptionType;
  name: string;
  label: string;
  price_modifier: number;
  sort_order: number;
  icon: string | null;
  hex_color: string | null;
  is_active: boolean;
  created_at: string;
}

interface FormData {
  name: string;
  label: string;
  price_modifier: number;
  sort_order: number;
  icon: string;
  hex_color: string;
  is_active: boolean;
}

const TABS: Array<{ type: OptionType; label: string; icon: string }> = [
  { type: "size", label: "Kích thước", icon: "📏" },
  { type: "flavor", label: "Vị bánh", icon: "🍰" },
  { type: "topping", label: "Topping", icon: "🌸" },
  { type: "color", label: "Màu sắc", icon: "🎨" },
];

const DEFAULT_FORM: FormData = {
  name: "",
  label: "",
  price_modifier: 0,
  sort_order: 0,
  icon: "",
  hex_color: "",
  is_active: true,
};

function formatPrice(price: number): string {
  if (price === 0) return "Miễn phí";
  return "+" + new Intl.NumberFormat("vi-VN").format(price) + "đ";
}

export default function AdminOptionsPage() {
  const [activeTab, setActiveTab] = useState<OptionType>("size");
  const [options, setOptions] = useState<CakeOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingOption, setEditingOption] = useState<CakeOption | null>(null);
  const [formData, setFormData] = useState<FormData>(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  // Delete confirm
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Track the latest fetch request to discard stale responses (race condition guard)
  const fetchRequestId = useRef(0);

  const fetchOptions = useCallback(async () => {
    setLoading(true);
    setError(null);
    const currentId = ++fetchRequestId.current;
    try {
      const data = await apiClient.get<{ options: CakeOption[] }>(
        `/api/v1/admin/options?type=${activeTab}`
      );
      // Only apply if this is still the latest request
      if (currentId === fetchRequestId.current) {
        setOptions(data.options);
      }
    } catch {
      if (currentId === fetchRequestId.current) {
        setError("Không thể tải danh sách thuộc tính. Vui lòng thử lại.");
      }
    } finally {
      if (currentId === fetchRequestId.current) {
        setLoading(false);
      }
    }
  }, [activeTab]);

  useEffect(() => {
    fetchOptions();
  }, [fetchOptions]);

  function openCreateModal() {
    setEditingOption(null);
    const maxSortOrder = options.reduce((max, o) => Math.max(max, o.sort_order), 0);
    setFormData({ ...DEFAULT_FORM, sort_order: maxSortOrder + 1 });
    setFormError("");
    setShowModal(true);
  }

  function openEditModal(option: CakeOption) {
    setEditingOption(option);
    setFormData({
      name: option.name,
      label: option.label,
      price_modifier: option.price_modifier,
      sort_order: option.sort_order,
      icon: option.icon || "",
      hex_color: option.hex_color || "",
      is_active: option.is_active,
    });
    setFormError("");
    setShowModal(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setFormError("");
    setSubmitting(true);

    try {
      const payload = {
        type: activeTab,
        name: formData.name.trim(),
        label: formData.label.trim(),
        price_modifier: formData.price_modifier,
        sort_order: formData.sort_order,
        icon: formData.icon.trim() || undefined,
        hex_color: formData.hex_color.trim() || undefined,
        is_active: formData.is_active,
      };

      if (editingOption) {
        await apiClient.put(`/api/v1/admin/options/${editingOption.id}`, payload);
      } else {
        await apiClient.post("/api/v1/admin/options", payload);
      }

      setShowModal(false);
      fetchOptions();
    } catch (err: unknown) {
      const apiError = err as ApiError;
      const detail = apiError?.detail;
      setFormError(typeof detail === "string" ? detail : "Lưu thất bại. Vui lòng thử lại.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleStatus(option: CakeOption) {
    try {
      await apiClient.patch(`/api/v1/admin/options/${option.id}/status`, {
        is_active: !option.is_active,
      });
      fetchOptions();
    } catch {
      alert("Cập nhật trạng thái thất bại.");
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id);
    try {
      await apiClient.delete(`/api/v1/admin/options/${id}`);
      fetchOptions();
    } catch {
      alert("Xóa thất bại. Vui lòng thử lại.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-heading text-2xl md:text-3xl text-mocha font-bold">
            Thuộc tính bánh
          </h1>
          <p className="text-mocha/60 text-sm mt-1">
            Quản lý kích thước, vị bánh, topping và màu sắc hiển thị trong Cake Builder
          </p>
        </div>
        <button
          onClick={openCreateModal}
          id="create-option-btn"
          className="flex items-center gap-2 px-4 py-2.5 bg-pink-pastel text-white rounded-xl font-medium hover:bg-pink-pastel/90 transition-colors min-h-[44px]"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden="true">
            <path d="M12 5v14M5 12h14" />
          </svg>
          Thêm mới
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white rounded-2xl p-1 shadow-sm mb-6 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.type}
            onClick={() => setActiveTab(tab.type)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all whitespace-nowrap min-h-[44px] ${
              activeTab === tab.type
                ? "bg-pink-pastel text-white shadow-sm"
                : "text-mocha/70 hover:bg-cream hover:text-mocha"
            }`}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm mb-4 flex justify-between">
          <span>{error}</span>
          <button onClick={fetchOptions} className="underline">Thử lại</button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-white rounded-2xl p-4 animate-pulse h-16" />
          ))}
        </div>
      )}

      {/* Options List */}
      {!loading && !error && (
        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
          {options.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-5xl mb-3">🎂</div>
              <p className="text-mocha/60 mb-4">Chưa có thuộc tính nào</p>
              <button
                onClick={openCreateModal}
                className="px-5 py-2.5 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors"
              >
                Thêm thuộc tính đầu tiên
              </button>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-cream/50 border-b border-gray-100">
                <tr>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-mocha/50 uppercase tracking-wide">Tên / Nhãn</th>
                  {activeTab === "color" && (
                    <th className="text-left px-5 py-3 text-xs font-semibold text-mocha/50 uppercase tracking-wide">Màu</th>
                  )}
                  <th className="text-left px-5 py-3 text-xs font-semibold text-mocha/50 uppercase tracking-wide">Giá thêm</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-mocha/50 uppercase tracking-wide">Thứ tự</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-mocha/50 uppercase tracking-wide">Trạng thái</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-mocha/50 uppercase tracking-wide">Hành động</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {options.map((option) => (
                  <tr key={option.id} className={`hover:bg-cream/30 transition-colors ${!option.is_active ? "opacity-50" : ""}`}>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-2">
                        {option.icon && <span className="text-xl">{option.icon}</span>}
                        <div>
                          <p className="font-medium text-mocha text-sm">{option.label}</p>
                          <p className="text-xs text-mocha/40 font-mono">{option.name}</p>
                        </div>
                      </div>
                    </td>
                    {activeTab === "color" && (
                      <td className="px-5 py-3">
                        {option.hex_color && (
                          <div className="flex items-center gap-2">
                            <div
                              className="w-6 h-6 rounded-full border border-gray-200"
                              style={{ backgroundColor: option.hex_color }}
                            />
                            <span className="text-xs text-mocha/50 font-mono">{option.hex_color}</span>
                          </div>
                        )}
                      </td>
                    )}
                    <td className="px-5 py-3">
                      <span className={`text-sm font-medium ${option.price_modifier > 0 ? "text-pink-pastel" : "text-mocha/50"}`}>
                        {formatPrice(option.price_modifier)}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-mocha/60 text-sm">{option.sort_order}</td>
                    <td className="px-5 py-3">
                      <button
                        onClick={() => handleToggleStatus(option)}
                        className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                          option.is_active
                            ? "bg-green-100 text-green-700 hover:bg-green-200"
                            : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                        }`}
                      >
                        {option.is_active ? "Đang hiện" : "Đã ẩn"}
                      </button>
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(option)}
                          className="p-1.5 text-mocha/50 hover:text-mocha hover:bg-cream rounded-lg transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center"
                          title="Sửa"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Xóa thuộc tính "${option.label}"?`)) {
                              handleDelete(option.id);
                            }
                          }}
                          disabled={deletingId === option.id}
                          className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors min-w-[36px] min-h-[36px] flex items-center justify-center disabled:opacity-50"
                          title="Xóa"
                        >
                          {deletingId === option.id ? (
                            <div className="animate-spin w-4 h-4 border-2 border-red-400 border-t-transparent rounded-full" />
                          ) : (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-mocha/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
            <div className="flex items-center justify-between p-5 border-b border-gray-100">
              <h2 className="font-heading text-lg font-bold text-mocha">
                {editingOption ? "Sửa thuộc tính" : "Thêm thuộc tính mới"}
              </h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-mocha/50 hover:text-mocha transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-5 space-y-4">
              {formError && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm">
                  {formError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-mocha mb-1">
                    Tên (key) <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    placeholder="vd: 6_inch, matcha..."
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-mocha mb-1">
                    Nhãn hiển thị <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={formData.label}
                    onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                    required
                    placeholder="vd: 6 inch (4-8 người)..."
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-mocha mb-1">Giá thêm (VND)</label>
                  <input
                    type="number"
                    value={formData.price_modifier}
                    onChange={(e) => setFormData({ ...formData, price_modifier: parseInt(e.target.value) || 0 })}
                    min={0}
                    step={1000}
                    placeholder="0"
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-mocha mb-1">Thứ tự hiển thị</label>
                  <input
                    type="number"
                    value={formData.sort_order}
                    onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                    min={0}
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-mocha mb-1">Icon (emoji)</label>
                  <input
                    type="text"
                    value={formData.icon}
                    onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
                    placeholder="vd: 🌸"
                    maxLength={5}
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel"
                  />
                </div>
                {activeTab === "color" && (
                  <div>
                    <label className="block text-sm font-medium text-mocha mb-1">Màu hex</label>
                    <div className="flex gap-2">
                      <input
                        type="color"
                        value={formData.hex_color || "#000000"}
                        onChange={(e) => setFormData({ ...formData, hex_color: e.target.value })}
                        className="w-12 h-10 rounded-lg border border-gray-200 cursor-pointer p-0.5"
                      />
                      <input
                        type="text"
                        value={formData.hex_color}
                        onChange={(e) => setFormData({ ...formData, hex_color: e.target.value })}
                        placeholder="#F4A7B9"
                        className="flex-1 px-3 py-2.5 rounded-xl border border-gray-200 text-sm text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 focus:border-pink-pastel"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex items-center gap-3">
                <input
                  id="is-active-checkbox"
                  type="checkbox"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="w-4 h-4 text-pink-pastel rounded"
                />
                <label htmlFor="is-active-checkbox" className="text-sm text-mocha cursor-pointer">
                  Hiển thị trong Cake Builder
                </label>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 py-2.5 border border-gray-200 text-mocha rounded-xl text-sm font-medium hover:bg-cream transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex-1 py-2.5 bg-pink-pastel text-white rounded-xl text-sm font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-50"
                >
                  {submitting ? "Đang lưu..." : editingOption ? "Lưu thay đổi" : "Thêm mới"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

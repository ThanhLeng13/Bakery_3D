"use client";

/**
 * Baker Inventory Management — /baker/inventory
 * Bếp quản lý lô bánh ngọt: xem, thêm, ẩn/hiện lô hàng theo chi nhánh.
 */

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuthContext } from "@/contexts/AuthContext";
import { apiClient } from "@/lib/api";

interface Product {
  id: string;
  name: string;
  category: string;
  product_type: string;
  base_price: number;
}

interface Branch {
  id: string;
  name: string;
  address?: string;
  phone?: string;
}

interface Batch {
  id: string;
  product_id: string;
  quantity: number;
  quantity_sold: number;
  quantity_available: number;
  produced_at: string;
  expires_at: string;
  notes: string | null;
  is_active: boolean;
  is_expired: boolean;
  branch_id: string | null;
  created_at: string;
  products?: { name: string; category: string };
  branches?: { id: string; name: string } | null;
}

const BRANCH_COLORS: Record<number, { bg: string; text: string; badge: string }> = {
  0: { bg: "bg-blue-50", text: "text-blue-700", badge: "bg-blue-100 text-blue-700" },
  1: { bg: "bg-purple-50", text: "text-purple-700", badge: "bg-purple-100 text-purple-700" },
  2: { bg: "bg-teal-50", text: "text-teal-700", badge: "bg-teal-100 text-teal-700" },
};

function formatPrice(price: number): string {
  return new Intl.NumberFormat("vi-VN").format(price) + "đ";
}

function formatDate(d: string): string {
  return new Date(d).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function inThreeDays(): string {
  const d = new Date();
  d.setDate(d.getDate() + 3);
  return d.toISOString().slice(0, 10);
}

function InventoryContent() {
  const router = useRouter();
  const { user } = useAuthContext();

  const [branches, setBranches] = useState<Branch[]>([]);
  const [selectedBranchId, setSelectedBranchId] = useState<string>("all");

  const [sweetProducts, setSweetProducts] = useState<Product[]>([]);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedProductId, setSelectedProductId] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Add batch form
  const [showAddForm, setShowAddForm] = useState(false);
  const [addQty, setAddQty] = useState("10");
  const [addProduced, setAddProduced] = useState(today());
  const [addExpires, setAddExpires] = useState(inThreeDays());
  const [addNotes, setAddNotes] = useState("");
  const [addBranchId, setAddBranchId] = useState<string>("");
  const [addLoading, setAddLoading] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Bàn phím điều hướng suggestions
  const [highlightIndex, setHighlightIndex] = useState<number>(-1);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Load branches
  useEffect(() => {
    apiClient
      .get<{ branches: Branch[] }>("/api/v1/branches")
      .then((res) => {
        const list = res.branches || [];
        setBranches(list);
        if (list.length > 0) setAddBranchId(list[0].id);
      })
      .catch(() => {/* silently ignore, branches are optional */});
  }, []);

  // Load sweet products — không tự chọn sản phẩm đầu tiên
  useEffect(() => {
    apiClient
      .get<{ products: Product[] }>("/api/v1/products?category=b%C3%A1nh+ng%E1%BB%8Dt&page_size=100")
      .then((res) => {
        const sweets = (res.products || []).filter((p) => p.product_type === "sweet");
        setSweetProducts(sweets);
        // Không tự điền sản phẩm đầu — để user tự tìm
      })
      .catch(() => setError("Không thể tải danh sách sản phẩm."));
  }, []);

  const loadBatches = useCallback(() => {
    if (!selectedProductId) return;
    setLoading(true);
    setError(null);
    // Luôn fetch TẤT CẢ lô để summary cards luôn đúng
    const allUrl = `/api/v1/baker/batches?product_id=${selectedProductId}`;
    apiClient
      .get<{ batches: Batch[] }>(allUrl)
      .then((res) => setBatches(res.batches || []))
      .catch(() => setError("Không thể tải lô hàng."))
      .finally(() => setLoading(false));
  }, [selectedProductId]);

  useEffect(() => {
    loadBatches();
  }, [loadBatches]);

  async function handleAddBatch(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProductId) return;

    setAddLoading(true);
    setAddError(null);

    const payload = {
      product_id: selectedProductId,
      quantity: parseInt(addQty, 10),
      produced_at: addProduced,
      expires_at: addExpires,
      notes: addNotes.trim() || null,
    };

    try {
      if (addBranchId === "" && branches.length > 0) {
        // Bulk API — may return 207 partial success (2xx so apiClient won't throw)
        const res = await apiClient.post<{
          batches?: unknown[];
          errors?: { branch_id: string; error: string }[];
          succeeded_branch_ids?: string[];
          message?: string;
        }>("/api/v1/baker/batches/bulk", {
          ...payload,
          branch_ids: branches.map((b) => b.id),
        });

        if (res.errors && res.errors.length > 0) {
          // Partial failure (207): some branches succeeded, some failed
          // Refresh batch list so user sees what was created
          loadBatches();
          const failedNames = res.errors
            .map((e) => branches.find((b) => b.id === e.branch_id)?.name || e.branch_id)
            .join(", ");
          setAddError(
            `${res.message || "Lỗi một phần"}. Thất bại tại: ${failedNames}. ` +
            `Đã tạo ${res.batches?.length || 0} lô thành công. Chỉ cần thử lại cho chi nhánh lỗi.`
          );
          return; // keep form open
        }
      } else {
        // Một chi nhánh cụ thể (hoặc null)
        await apiClient.post("/api/v1/baker/batches", {
          ...payload,
          branch_id: addBranchId || null,
        });
      }

      setShowAddForm(false);
      setAddQty("10");
      setAddNotes("");
      setAddExpires(inThreeDays());
      loadBatches();
    } catch (err: unknown) {
      const e = err as { detail?: string };
      setAddError(e?.detail || "Không thể thêm lô hàng.");
    } finally {
      setAddLoading(false);
    }
  }

  async function toggleBatch(batchId: string, currentActive: boolean) {
    try {
      await apiClient.patch(`/api/v1/baker/batches/${batchId}`, {
        is_active: !currentActive,
      });
      loadBatches();
    } catch {
      setError("Không thể cập nhật lô hàng.");
    }
  }

  const selectedProduct = sweetProducts.find((p) => p.id === selectedProductId);

  // filteredBatches: lọc client-side theo chi nhánh đang chọn
  const filteredBatches = selectedBranchId === "all"
    ? batches
    : batches.filter((b) => b.branch_id === selectedBranchId);

  // totalAvailable: tính từ filteredBatches để badge sản phẩm phản ánh đúng filter
  const totalAvailable = filteredBatches
    .filter((b) => b.is_active && !b.is_expired)
    .reduce((sum, b) => sum + b.quantity_available, 0);

  // Summary by branch: dùng batches (luôn chứa toàn bộ lô) để card luôn đúng
  const branchSummary = branches.map((branch, i) => {
    const branchBatches = batches.filter((b) => b.branch_id === branch.id && b.is_active && !b.is_expired);
    const total = branchBatches.reduce((sum, b) => sum + b.quantity_available, 0);
    const color = BRANCH_COLORS[i % 3];
    return { ...branch, total, color };
  });

  return (
    <main className="min-h-screen bg-cream">
      <div className="max-w-5xl mx-auto px-4 py-8">

          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <Link
                href="/"
                className="font-heading text-lg text-mocha font-bold flex items-center gap-1.5 hover:text-pink-pastel transition-colors"
                aria-label="Về trang chủ"
              >
                🎂 <span className="hidden sm:inline">Bơ Nơ</span>
              </Link>
              <div>
                <h1 className="text-2xl font-heading font-bold text-mocha">Quản lý kho bánh ngọt</h1>
                <p className="text-mocha/60 text-sm mt-0.5">Nhập lô hàng, quản lý hạn sử dụng và tồn kho theo chi nhánh</p>
              </div>
            </div>
            <button
              onClick={() => router.push("/baker/orders")}
              className="text-sm text-mocha/60 hover:text-mocha flex items-center gap-1.5 transition-colors"
            >
              ← Quay lại đơn hàng
            </button>
          </div>

          {/* Product search selector */}
          <div className="bg-white rounded-2xl p-4 mb-4 border border-mocha/5 shadow-sm">
            <label className="block text-sm font-medium text-mocha mb-2">Chọn sản phẩm bánh ngọt</label>
            <div className="relative">
              {/* Search input */}
              <div className="relative flex items-center">
                <svg
                  className="absolute left-3 w-4 h-4 text-mocha/40 pointer-events-none"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0" />
                </svg>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setHighlightIndex(-1);
                    setShowSuggestions(true);
                  }}
                  onFocus={() => {
                    setShowSuggestions(true);
                    setHighlightIndex(-1);
                  }}
                  onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                  onKeyDown={(e) => {
                    if (!showSuggestions) return;
                    const filtered = sweetProducts.filter((p) =>
                      p.name.toLowerCase().includes(searchQuery.toLowerCase())
                    );
                    if (filtered.length === 0) return;

                    if (e.key === "ArrowDown") {
                      e.preventDefault();
                      const next = Math.min(highlightIndex + 1, filtered.length - 1);
                      setHighlightIndex(next);
                      // Scroll item vào view
                      const el = suggestionsRef.current?.children[next] as HTMLElement;
                      el?.scrollIntoView({ block: "nearest" });
                    } else if (e.key === "ArrowUp") {
                      e.preventDefault();
                      // Cho phép giảm về -1; clamp tại -1 để không xuống -2, -3...
                      const prev = Math.max(-1, highlightIndex - 1);
                      setHighlightIndex(prev);
                      if (prev >= 0) {
                        const el = suggestionsRef.current?.children[prev] as HTMLElement;
                        el?.scrollIntoView({ block: "nearest" });
                      }
                    } else if (e.key === "Enter") {
                      // Chỉ chọn khi đang highlight một item cụ thể
                      if (highlightIndex >= 0) {
                        const chosen = filtered[highlightIndex];
                        if (chosen) {
                          e.preventDefault();
                          setSelectedProductId(chosen.id);
                          setSearchQuery(chosen.name);
                          setShowSuggestions(false);
                          setHighlightIndex(-1);
                        }
                      }
                    } else if (e.key === "Tab") {
                      // Tab chọn item highlight (không preventDefault — focus vẫn chuyển tiếp)
                      if (highlightIndex >= 0) {
                        const chosen = filtered[highlightIndex];
                        if (chosen) {
                          setSelectedProductId(chosen.id);
                          setSearchQuery(chosen.name);
                          setShowSuggestions(false);
                          setHighlightIndex(-1);
                        }
                      }
                    } else if (e.key === "Escape") {
                      setShowSuggestions(false);
                      setHighlightIndex(-1);
                    }
                  }}
                  placeholder="Tìm tên bánh..."
                  className="w-full border border-mocha/20 rounded-xl pl-9 pr-10 py-2.5 text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/40 focus:border-pink-pastel/40 transition-all"
                />
                {/* Clear button */}
                {searchQuery && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchQuery("");
                      setSelectedProductId("");
                      setShowSuggestions(true);
                      setHighlightIndex(-1);
                    }}
                    className="absolute right-3 text-mocha/30 hover:text-mocha/60 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>

              {/* Suggestions dropdown */}
              {showSuggestions && (() => {
                const filtered = sweetProducts.filter((p) =>
                  p.name.toLowerCase().includes(searchQuery.toLowerCase())
                );
                return filtered.length > 0 ? (
                  <div
                    ref={suggestionsRef}
                    className="absolute z-30 top-full left-0 right-0 mt-1 bg-white rounded-2xl border border-mocha/10 shadow-lg overflow-hidden max-h-60 overflow-y-auto"
                  >
                    {filtered.map((p, idx) => {
                      const isKeyboardHighlighted = idx === highlightIndex;
                      const isSelected = selectedProductId === p.id;
                      return (
                        <button
                          key={p.id}
                          type="button"
                          onMouseEnter={() => setHighlightIndex(idx)}
                          onMouseDown={() => {
                            setSelectedProductId(p.id);
                            setSearchQuery(p.name);
                            setShowSuggestions(false);
                            setHighlightIndex(-1);
                          }}
                          className={`w-full text-left px-4 py-3 text-sm transition-colors flex items-center justify-between gap-2 ${
                            isKeyboardHighlighted
                              ? "bg-pink-pastel/20 text-pink-pastel font-medium"
                              : isSelected
                                ? "bg-pink-pastel/10 text-pink-pastel font-medium"
                                : "text-mocha hover:bg-cream"
                          }`}
                        >
                          <span>{p.name}</span>
                          <span className="text-xs text-mocha/40 flex-shrink-0">{formatPrice(p.base_price)}</span>
                        </button>
                      );
                    })}
                  </div>
                ) : searchQuery ? (
                  <div className="absolute z-30 top-full left-0 right-0 mt-1 bg-white rounded-2xl border border-mocha/10 shadow-lg px-4 py-3 text-sm text-mocha/50">
                    Không tìm thấy sản phẩm nào
                  </div>
                ) : null;
              })()}
            </div>

            {selectedProduct && (
              <div className="mt-3 flex items-center gap-4 text-sm flex-wrap">
                <span className="text-mocha/60">Giá cơ bản: <strong className="text-mocha">{formatPrice(selectedProduct.base_price)}</strong></span>
                <span className={`font-semibold px-2 py-0.5 rounded-full text-xs ${totalAvailable > 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-600"}`}>
                  {totalAvailable > 0 ? `Tổng còn ${totalAvailable} cái` : "Hết hàng"}
                </span>
              </div>
            )}
          </div>

          {/* Branch summary cards — bao gồm card "Tất cả" */}
          {branches.length > 0 && selectedProduct && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              {/* Card Tất cả chi nhánh */}
              <button
                onClick={() => setSelectedBranchId("all")}
                className={`rounded-2xl p-4 border-2 text-left transition-all ${
                  selectedBranchId === "all"
                    ? "border-pink-pastel bg-pink-pastel/5"
                    : "border-mocha/10 bg-white hover:border-mocha/20"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-mocha/60">🏬 Tất cả</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    selectedBranchId === "all"
                      ? "bg-pink-pastel/20 text-pink-pastel"
                      : "bg-mocha/10 text-mocha/60"
                  }`}>
                    {/* Tính từ batches (luôn chứa toàn bộ lô, kể cả Kho chung branch_id=null) */}
                    {batches.filter(b => b.is_active && !b.is_expired).reduce((s, b) => s + b.quantity_available, 0)} cái
                  </span>
                </div>
                <p className="text-xs text-mocha/40 truncate">Tất cả chi nhánh</p>
              </button>

              {/* Card từng chi nhánh */}
              {branchSummary.map((b) => (
                <button
                  key={b.id}
                  onClick={() => setSelectedBranchId(b.id)}
                  className={`rounded-2xl p-4 border-2 text-left transition-all ${
                    selectedBranchId === b.id
                      ? `border-pink-pastel ${b.color.bg}`
                      : "border-mocha/10 bg-white hover:border-mocha/20"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-mocha/60">🏪 {b.name}</span>
                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${b.color.badge}`}>
                      {b.total} cái
                    </span>
                  </div>
                  {b.address && <p className="text-xs text-mocha/40 truncate">{b.address}</p>}
                </button>
              ))}
            </div>
          )}

          {/* Add batch button */}
          <div className="flex justify-between items-center mb-3 gap-3 flex-wrap">
            <div className="flex items-center gap-2">
              <h2 className="font-semibold text-mocha">Các lô hàng hiện có</h2>
              {selectedBranchId !== "all" && (
                <span className="text-xs bg-pink-pastel/10 text-pink-pastel px-2 py-0.5 rounded-full font-medium">
                  {branches.find(b => b.id === selectedBranchId)?.name}
                  <button onClick={() => setSelectedBranchId("all")} className="ml-1 hover:text-pink-pastel/70">×</button>
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  if (!showAddForm) {
                    // Đồng bộ chi nhánh form với chi nhánh đang được lọc
                    if (selectedBranchId !== "all") {
                      setAddBranchId(selectedBranchId);
                    } else {
                      setAddBranchId(""); // "" = kho chung / chưa gắn chi nhánh
                    }
                  }
                  setShowAddForm(!showAddForm);
                }}
                disabled={!selectedProductId}
                title={!selectedProductId ? "Hãy chọn sản phẩm trước" : undefined}
                className="flex items-center gap-1.5 px-4 py-2 bg-pink-pastel text-white rounded-full text-sm font-medium hover:bg-pink-pastel/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Thêm lô mới
              </button>
            </div>
          </div>

          {/* Add batch form */}
          {showAddForm && (
            <form
              onSubmit={handleAddBatch}
              className="bg-white rounded-2xl p-5 mb-4 border border-pink-pastel/20 shadow-sm space-y-4"
            >
              <h3 className="font-semibold text-mocha">Nhập lô bánh mới</h3>
              {addError && (
                <p className="text-red-600 text-sm bg-red-50 rounded-lg px-3 py-2">{addError}</p>
              )}

              {/* Branch selector */}
              {branches.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-mocha/70 mb-2">Chọn chi nhánh</label>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">

                    {/* Card Tất cả / Kho chung */}
                    <button
                      type="button"
                      onClick={() => {
                        setAddBranchId("");
                        setSelectedBranchId("all");
                      }}
                      className={`rounded-xl px-3 py-2.5 text-sm font-medium border-2 transition-all text-left ${
                        addBranchId === ""
                          ? "border-pink-pastel bg-pink-pastel/5 text-pink-pastel"
                          : "border-mocha/15 text-mocha/70 hover:border-mocha/30"
                      }`}
                    >
                      🏬 Tất cả chi nhánh
                      <p className="text-xs font-normal text-mocha/40 mt-0.5 truncate">Mỗi CN nhận {addQty || "0"} cái</p>
                    </button>

                    {/* Card từng chi nhánh */}
                    {branches.map((branch, i) => {
                      const color = BRANCH_COLORS[i % 3];
                      return (
                        <button
                          key={branch.id}
                          type="button"
                          onClick={() => {
                            setAddBranchId(branch.id);
                            setSelectedBranchId(branch.id); // đồng bộ filter bên trên
                          }}
                          className={`rounded-xl px-3 py-2.5 text-sm font-medium border-2 transition-all text-left ${
                            addBranchId === branch.id
                              ? `border-pink-pastel ${color.bg} ${color.text}`
                              : "border-mocha/15 text-mocha/70 hover:border-mocha/30"
                          }`}
                        >
                          🏪 {branch.name}
                          {branch.address && (
                            <p className="text-xs font-normal text-mocha/40 mt-0.5 truncate">{branch.address}</p>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-mocha/70 mb-1">Số lượng (cái)</label>
                  <input
                    type="number"
                    min={1}
                    max={9999}
                    value={addQty}
                    onChange={(e) => setAddQty(e.target.value)}
                    required
                    className="w-full border border-mocha/20 rounded-xl px-3 py-2 text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-mocha/70 mb-1">Ngày sản xuất</label>
                  <input
                    type="date"
                    value={addProduced}
                    onChange={(e) => setAddProduced(e.target.value)}
                    required
                    className="w-full border border-mocha/20 rounded-xl px-3 py-2 text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-mocha/70 mb-1">Ngày hết hạn SD</label>
                  <input
                    type="date"
                    value={addExpires}
                    onChange={(e) => setAddExpires(e.target.value)}
                    min={addProduced}
                    required
                    className="w-full border border-mocha/20 rounded-xl px-3 py-2 text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-mocha/70 mb-1">Ghi chú (tùy chọn)</label>
                <input
                  type="text"
                  value={addNotes}
                  onChange={(e) => setAddNotes(e.target.value)}
                  placeholder="VD: Lô sáng, dùng bơ mới..."
                  maxLength={300}
                  className="w-full border border-mocha/20 rounded-xl px-3 py-2 text-mocha focus:outline-none focus:ring-2 focus:ring-pink-pastel/30 placeholder-mocha/30"
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={addLoading}
                  className="px-5 py-2 bg-pink-pastel text-white rounded-full font-medium text-sm hover:bg-pink-pastel/90 transition-colors disabled:opacity-60"
                >
                  {addLoading ? "Đang lưu..." : "Lưu lô hàng"}
                </button>
                <button
                  type="button"
                  onClick={() => { setShowAddForm(false); setAddError(null); }}
                  className="px-5 py-2 text-mocha/60 border border-mocha/20 rounded-full text-sm hover:bg-mocha/5 transition-colors"
                >
                  Hủy
                </button>
              </div>
            </form>
          )}

          {error && (
            <p className="text-red-600 text-sm bg-red-50 rounded-xl px-4 py-3 mb-3">{error}</p>
          )}

          {/* Batches list */}
          {!selectedProductId ? (
            <div className="bg-white rounded-2xl p-10 text-center border border-mocha/5 shadow-sm">
              <p className="text-3xl mb-3">🔍</p>
              <p className="text-mocha/60 font-medium">Hãy tìm và chọn một sản phẩm ở ô phía trên để xem các lô hàng.</p>
            </div>
          ) : loading ? (
            <div className="text-center py-12 text-mocha/40">Đang tải...</div>
          ) : filteredBatches.length === 0 ? (
            <div className="bg-white rounded-2xl p-8 text-center border border-mocha/5 shadow-sm">
              <p className="text-mocha/50">
                {selectedBranchId === "all"
                  ? "Chưa có lô hàng nào. Hãy thêm lô đầu tiên!"
                  : `Không có lô nào tại ${branches.find(b => b.id === selectedBranchId)?.name || "chi nhánh này"}.`}
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredBatches.map((batch) => {
                const isExpired = batch.is_expired;
                const isEmpty = batch.quantity_available <= 0;
                const statusColor = !batch.is_active
                  ? "bg-gray-100 border-gray-200"
                  : isExpired
                    ? "bg-red-50 border-red-200"
                    : isEmpty
                      ? "bg-amber-50 border-amber-200"
                      : "bg-green-50 border-green-200";

                const branchIndex = batch.branches
                  ? branches.findIndex((b) => b.id === batch.branch_id)
                  : -1;
                const branchColor = branchIndex >= 0 ? BRANCH_COLORS[branchIndex % 3] : null;

                return (
                  <div
                    key={batch.id}
                    className={`rounded-2xl p-4 border flex flex-col sm:flex-row sm:items-center gap-3 ${statusColor} ${!batch.is_active ? "opacity-60" : ""}`}
                  >
                    {/* Status indicator */}
                    <div className="flex-1">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                          !batch.is_active ? "bg-gray-200 text-gray-600"
                          : isExpired ? "bg-red-200 text-red-700"
                          : isEmpty ? "bg-amber-200 text-amber-700"
                          : "bg-green-200 text-green-700"
                        }`}>
                          {!batch.is_active ? "Ẩn" : isExpired ? "Hết hạn" : isEmpty ? "Hết hàng" : `Còn ${batch.quantity_available} cái`}
                        </span>
                        <span className="text-xs text-mocha/50">
                          Đã bán {batch.quantity_sold}/{batch.quantity}
                        </span>
                        {/* Branch badge */}
                        {batch.branches && branchColor && (
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${branchColor.badge}`}>
                            🏪 {batch.branches.name}
                          </span>
                        )}
                        {!batch.branch_id && (
                          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-mocha/10 text-mocha/50">
                            Chưa gắn CN
                          </span>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-mocha/70">
                        <span>SX: {formatDate(batch.produced_at)}</span>
                        <span className={isExpired ? "text-red-600 font-medium" : ""}>
                          HSD: {formatDate(batch.expires_at)}
                        </span>
                      </div>

                      {batch.notes && (
                        <p className="text-xs text-mocha/50 mt-1 italic">{batch.notes}</p>
                      )}
                    </div>

                    {/* Toggle active */}
                    <button
                      onClick={() => toggleBatch(batch.id, batch.is_active)}
                      className={`flex-shrink-0 px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                        batch.is_active
                          ? "bg-white border border-mocha/20 text-mocha/70 hover:bg-mocha/5"
                          : "bg-pink-pastel/10 border border-pink-pastel/30 text-pink-pastel hover:bg-pink-pastel/20"
                      }`}
                    >
                      {batch.is_active ? "Ẩn lô" : "Hiện lô"}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
      </div>
    </main>
  );
}

export default function BakerInventoryPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-cream" />}>
      <ProtectedRoute allowedRoles={["baker", "admin"]}>
        <InventoryContent />
      </ProtectedRoute>
    </Suspense>
  );
}

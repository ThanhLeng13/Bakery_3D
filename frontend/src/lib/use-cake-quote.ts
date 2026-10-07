"use client";

/**
 * Lấy giá bánh tùy chỉnh từ server.
 *
 * Vì sao không tự tính ở frontend
 * ------------------------------
 * Trước đây có ba bảng giá rời rạc (BASE_PRICES trong price-calculator.ts,
 * SIZE_PRICES trong checkout, và bảng phía backend). Chúng lệch nhau: Studio
 * hiện 480.000đ cho 20cm + hoa + viền rosettes, nhưng đơn bị tính 350.000đ —
 * chênh 130.000đ. Nhân bản bảng giá chính là nguồn của lỗi đó.
 *
 * Quyết định 07/10/2026: server là nguồn quyết định duy nhất. Giao diện chỉ
 * hiển thị con số server trả về, nên hiển thị và thu tiền không thể lệch nhau.
 *
 * Endpoint: POST /api/v1/orders/quote
 */

import { useEffect, useState } from "react";
import { apiClient } from "@/lib/api";
import type { CakeDesign } from "@/types";

export interface QuoteBreakdown {
  base_price: number;
  topping_cost: number;
  decoration_cost: number;
  total: number;
  lead_hours: number;
}

interface QuoteState {
  quote: QuoteBreakdown | null;
  loading: boolean;
  error: string | null;
}

/**
 * Báo giá một cấu hình bánh. Debounce 300ms vì Studio gọi lại mỗi lần khách
 * đổi topping hoặc trang trí.
 */
export function useCakeQuote(design: CakeDesign | null): QuoteState {
  const [quote, setQuote] = useState<QuoteBreakdown | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Khoá phụ thuộc theo giá trị thật của cấu hình, không theo tham chiếu object,
  // để không gọi lại API mỗi lần component render.
  const signature = design ? JSON.stringify(design) : null;

  useEffect(() => {
    if (!design || !signature) {
      setQuote(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    const timer = setTimeout(() => {
      apiClient
        .post<QuoteBreakdown>("/api/v1/orders/quote", { design })
        .then((res) => {
          if (!cancelled) setQuote(res);
        })
        .catch((err) => {
          if (cancelled) return;
          setQuote(null);
          setError(
            err instanceof Error
              ? err.message
              : "Không lấy được giá. Vui lòng thử lại."
          );
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [signature, design]);

  return { quote, loading, error };
}

"use client";

/**
 * LoyaltyContext — Global loyalty state shared across the entire app.
 *
 * Giải quyết 2 vấn đề của local useLoyalty hook:
 *   1. Loại bỏ duplicate API calls: Header + LoyaltyPage cùng dùng 1 state,
 *      chỉ fetch 1 lần khi mount (hoặc khi user thay đổi).
 *   2. Badge điểm trên Header tự động cập nhật sau khi đổi điểm thành công
 *      trên LoyaltyPage — không cần reload trang.
 *
 * Usage:
 *   - Wrap ứng dụng bằng <LoyaltyProvider> trong layout.tsx
 *   - Dùng useLoyaltyContext() thay cho useLoyalty() trong Header và LoyaltyPage
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import { getStoredUser, getStoredToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types (re-exported so consumers don't need to import from useLoyalty) ────

export interface LoyaltyTransaction {
  id: string;
  points: number;
  type: "purchase" | "order" | "redeem";
  ref_id: string | null;
  note: string | null;
  created_at: string;
}

export interface LoyaltyData {
  points: number;
  total_earned: number;
  voucher_value: number;
  points_per_voucher: number;
  available_vouchers: number;
  points_to_next_voucher: number;
  transactions: LoyaltyTransaction[];
  updated_at: string | null;
}

interface RedeemResult {
  voucher_codes: string[];
  discount_vnd: number;
  points_used: number;
  remaining_points: number;
  message: string;
}

interface LoyaltyContextValue {
  data: LoyaltyData | null;
  loading: boolean;
  error: string | null;
  /** Refresh balance từ server (fire-and-forget safe). */
  refresh: () => Promise<void>;
  /** Đổi điểm: gọi API rồi tự refresh balance. */
  redeemPoints: (voucherCount: number) => Promise<RedeemResult>;
}

// ─── Context ──────────────────────────────────────────────────────────────────

const LoyaltyContext = createContext<LoyaltyContextValue | null>(null);

export function LoyaltyProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<LoyaltyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLoyalty = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/api/v1/loyalty/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error(`Lỗi ${res.status}: ${res.statusText}`);
      }

      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Không thể tải thông tin điểm."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch khi user đã đăng nhập
  useEffect(() => {
    const user = getStoredUser();
    if (user) fetchLoyalty();
    else setLoading(false);
  }, [fetchLoyalty]);

  const redeemPoints = useCallback(
    async (voucherCount: number): Promise<RedeemResult> => {
      const token = getStoredToken();
      if (!token) throw new Error("Bạn cần đăng nhập.");

      const res = await fetch(`${API_BASE}/api/v1/loyalty/redeem`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ voucher_count: voucherCount }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Lỗi ${res.status}`);
      }

      const result: RedeemResult = await res.json();
      // Refresh balance fire-and-forget — không để lỗi refresh làm hỏng kết quả
      fetchLoyalty().catch((err) =>
        console.warn("[LoyaltyContext] refresh after redeem failed:", err)
      );
      return result;
    },
    [fetchLoyalty]
  );

  return (
    <LoyaltyContext.Provider
      value={{ data, loading, error, refresh: fetchLoyalty, redeemPoints }}
    >
      {children}
    </LoyaltyContext.Provider>
  );
}

export function useLoyaltyContext(): LoyaltyContextValue {
  const ctx = useContext(LoyaltyContext);
  if (!ctx) {
    throw new Error(
      "useLoyaltyContext must be used inside <LoyaltyProvider>. " +
        "Wrap your app with <LoyaltyProvider> in layout.tsx."
    );
  }
  return ctx;
}

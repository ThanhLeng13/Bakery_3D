"use client";

/**
 * useLoyalty — Hook lấy thông tin điểm tích lũy của khách hàng.
 *
 * Tự động fetch khi user đăng nhập.
 * Cung cấp hàm redeemPoints để đổi điểm lấy voucher.
 */

import { useState, useEffect, useCallback } from "react";
import { getStoredUser, getStoredToken } from "@/lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LoyaltyTransaction {
  id: string;
  points: number;           // dương = cộng, âm = trừ
  type: "purchase" | "order" | "redeem";
  ref_id: string | null;
  note: string | null;
  created_at: string;
}

export interface LoyaltyData {
  points: number;
  total_earned: number;
  voucher_value: number;            // VND mỗi voucher
  points_per_voucher: number;       // điểm cần cho 1 voucher
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

export function useLoyalty() {
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
      setError(err instanceof Error ? err.message : "Không thể tải thông tin điểm.");
    } finally {
      setLoading(false);
    }
  }, []);

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
      // Refresh balance fire-and-forget — redeem đã thành công nên không để
      // lỗi refresh làm hỏng kết quả trả về cho caller.
      fetchLoyalty().catch((err) =>
        console.warn("[useLoyalty] fetchLoyalty after redeem failed:", err)
      );
      return result;
    },
    [fetchLoyalty]
  );

  return { data, loading, error, refresh: fetchLoyalty, redeemPoints };
}

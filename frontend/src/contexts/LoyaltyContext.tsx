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
  useMemo,
  useRef,
  ReactNode,
} from "react";
import { getStoredToken } from "@/lib/auth";
import { useAuthContext } from "@/contexts/AuthContext";

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
  const { isAuthenticated, user } = useAuthContext();

  const [data, setData] = useState<LoyaltyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // The role is read through a ref so `fetchLoyalty` keeps a stable identity.
  // Previously it closed over `user?.role`, so every time AuthContext produced a
  // new user object the callback changed, the effect below re-ran, and the same
  // balance was fetched again. The ref keeps the value current without making
  // it a dependency.
  const roleRef = useRef<string | undefined>(user?.role);
  roleRef.current = user?.role;

  // Coalesces concurrent calls, keyed by the auth token that started them.
  // A plain boolean was wrong: if the user signed out and another signed in
  // while a request was still open, the stale flag blocked the new user's
  // request, and the previous user's response could still land in state.
  // Holding the token lets a new identity start a fresh request and lets a
  // late response be discarded when it no longer matches the active token.
  const inFlightTokenRef = useRef<string | null>(null);

  const fetchLoyalty = useCallback(async () => {
    const token = getStoredToken();

    if (!token || roleRef.current !== "customer") {
      inFlightTokenRef.current = null;
      setData(null);
      setLoading(false);
      return;
    }

    if (inFlightTokenRef.current === token) return;
    inFlightTokenRef.current = token;

    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${API_BASE}/api/v1/loyalty/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      // The user may have switched accounts while this was open; drop a
      // response that no longer belongs to the active session.
      if (inFlightTokenRef.current !== token) return;

      if (!res.ok) {
        throw new Error(`Lỗi ${res.status}: ${res.statusText}`);
      }

      const json = await res.json();
      if (inFlightTokenRef.current !== token) return;
      setData(json);
    } catch (err) {
      if (inFlightTokenRef.current !== token) return;
      setError(
        err instanceof Error ? err.message : "Không thể tải thông tin điểm."
      );
    } finally {
      if (inFlightTokenRef.current === token) {
        inFlightTokenRef.current = null;
        setLoading(false);
      }
    }
  }, []);

  // Re-run whenever authentication state changes:
  //   login  → isAuthenticated becomes true  → fetch loyalty data
  //   logout → isAuthenticated becomes false → clear stale data
  useEffect(() => {
    if (isAuthenticated && user?.role === "customer") {
      fetchLoyalty();
    } else {
      setData(null);
      setLoading(false);
      setError(null);
    }
  }, [isAuthenticated, user?.role, fetchLoyalty]);

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

  // Memoised so Header and LoyaltyPage do not re-render when the provider
  // re-renders for unrelated reasons (e.g. AuthProvider state changing above).
  const contextValue = useMemo(
    () => ({
      data,
      loading,
      error,
      refresh: fetchLoyalty,
      redeemPoints,
    }),
    [data, loading, error, fetchLoyalty, redeemPoints]
  );

  return (
    <LoyaltyContext.Provider value={contextValue}>
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

"use client";

/**
 * Trang Tích Điểm — Bơ Nơ Bakery
 *
 * Theme màu lấy từ linh vật avocado:
 *   xanh avocado đậm  #3d6b35
 *   xanh avocado nhạt #8cbd6e
 *   hồng nơ           #f4a0b5
 */

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import Header from "@/components/Header";
import { useLoyaltyContext, LoyaltyTransaction } from "@/contexts/LoyaltyContext";
import { useAuthContext } from "@/contexts/AuthContext";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatVND(amount: number): string {
  return amount.toLocaleString("vi-VN") + " VND";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TYPE_LABEL: Record<string, string> = {
  purchase: "🛒 Mua bánh ngọt",
  order: "🎂 Đặt bánh kem",
  redeem: "🎁 Đổi điểm",
};

const TYPE_COLOR: Record<string, string> = {
  purchase: "#8cbd6e",
  order: "#3d6b35",
  redeem: "#f4a0b5",
};

// ─── Transaction Row ──────────────────────────────────────────────────────────
function TransactionRow({ tx }: { tx: LoyaltyTransaction }) {
  const isPositive = tx.points > 0;
  const color = TYPE_COLOR[tx.type] || "#8cbd6e";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0.85rem 1rem",
        borderBottom: "1px solid rgba(61,107,53,0.08)",
        transition: "background 0.15s",
        gap: "1rem",
      }}
      onMouseEnter={(e) =>
        ((e.currentTarget as HTMLDivElement).style.background =
          "rgba(140,189,110,0.07)")
      }
      onMouseLeave={(e) =>
        ((e.currentTarget as HTMLDivElement).style.background = "transparent")
      }
    >
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flex: 1, minWidth: 0 }}>
        {/* Dot */}
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: color,
            flexShrink: 0,
            boxShadow: `0 0 6px ${color}80`,
          }}
        />
        <div style={{ minWidth: 0 }}>
          <p
            style={{
              fontSize: "0.875rem",
              fontWeight: 600,
              color: "#3d4a35",
              margin: 0,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {TYPE_LABEL[tx.type] || tx.type}
          </p>
          {tx.note && (
            <p
              style={{
                fontSize: "0.75rem",
                color: "#5c3d2e",
                opacity: 0.65,
                margin: 0,
                marginTop: "0.15rem",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {tx.note}
            </p>
          )}
        </div>
      </div>

      <div style={{ textAlign: "right", flexShrink: 0 }}>
        <p
          style={{
            fontWeight: 700,
            fontSize: "0.9rem",
            color: isPositive ? "#3d6b35" : "#e8837a",
            margin: 0,
          }}
        >
          {isPositive ? "+" : ""}
          {tx.points.toLocaleString("vi-VN")} điểm
        </p>
        <p style={{ fontSize: "0.7rem", color: "#5c3d2e", opacity: 0.5, margin: 0, marginTop: "0.1rem" }}>
          {formatDate(tx.created_at)}
        </p>
      </div>
    </div>
  );
}

// ─── Redeem Modal ─────────────────────────────────────────────────────────────
function RedeemModal({
  availableVouchers,
  voucherValue,
  pointsPerVoucher,
  onClose,
  onConfirm,
  loading,
  error,
}: {
  availableVouchers: number;
  voucherValue: number;
  pointsPerVoucher: number;
  onClose: () => void;
  onConfirm: (count: number) => void;
  loading: boolean;
  error?: string | null;
}) {
  const [count, setCount] = useState(1);
  // FIX: Enforce API cap of max 10 vouchers per redemption.
  const maxSelectable = Math.min(availableVouchers, 10);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(30,40,20,0.55)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "1rem",
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: "1.5rem",
          padding: "2rem",
          width: "100%",
          maxWidth: "420px",
          boxShadow: "0 20px 60px rgba(61,107,53,0.25)",
          animation: "slideUp 0.25s ease-out",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🎁</div>
          <h2
            style={{
              fontSize: "1.3rem",
              fontWeight: 700,
              color: "#3d6b35",
              margin: 0,
            }}
          >
            Đổi Điểm Lấy Voucher
          </h2>
          <p style={{ color: "#5c3d2e", opacity: 0.7, fontSize: "0.875rem", margin: "0.5rem 0 0" }}>
            {pointsPerVoucher} điểm = 1 voucher = {formatVND(voucherValue)} giảm giá
          </p>
        </div>

        {/* Count selector */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "1.5rem",
            margin: "1.5rem 0",
          }}
        >
          <button
            id="redeem-decrease"
            onClick={() => setCount(Math.max(1, count - 1))}
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              border: "2px solid #3d6b35",
              background: "white",
              color: "#3d6b35",
              fontSize: "1.25rem",
              fontWeight: 700,
              cursor: count <= 1 ? "not-allowed" : "pointer",
              opacity: count <= 1 ? 0.4 : 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.15s",
            }}
          >
            −
          </button>

          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontSize: "2.5rem",
                fontWeight: 800,
                color: "#3d6b35",
                lineHeight: 1,
              }}
            >
              {count}
            </div>
            <div style={{ fontSize: "0.75rem", color: "#5c3d2e", opacity: 0.6 }}>voucher</div>
          </div>

          <button
            id="redeem-increase"
            onClick={() => setCount(Math.min(maxSelectable, count + 1))}
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "50%",
              border: "2px solid #3d6b35",
              background: "#3d6b35",
              color: "white",
              fontSize: "1.25rem",
              fontWeight: 700,
              cursor: count >= maxSelectable ? "not-allowed" : "pointer",
              opacity: count >= maxSelectable ? 0.4 : 1,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.15s",
            }}
          >
            +
          </button>
        </div>

        {/* Summary */}
        <div
          style={{
            background: "rgba(140,189,110,0.12)",
            borderRadius: "1rem",
            padding: "1rem",
            textAlign: "center",
            marginBottom: "1.5rem",
          }}
        >
          <p style={{ margin: 0, color: "#3d6b35", fontWeight: 600 }}>
            Dùng {(count * pointsPerVoucher).toLocaleString("vi-VN")} điểm
          </p>
          <p style={{ margin: "0.25rem 0 0", color: "#3d6b35", fontSize: "1.1rem", fontWeight: 700 }}>
            Nhận {formatVND(count * voucherValue)} giảm giá
          </p>
        </div>

        {error && (
          <div style={{
            background: "#fff2f2",
            color: "#d32f2f",
            padding: "0.75rem",
            borderRadius: "0.5rem",
            fontSize: "0.875rem",
            marginBottom: "1.5rem",
            textAlign: "center",
            border: "1px solid #ffcdd2"
          }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            id="redeem-cancel"
            onClick={onClose}
            style={{
              flex: 1,
              padding: "0.85rem",
              borderRadius: "0.85rem",
              border: "2px solid rgba(61,107,53,0.25)",
              background: "transparent",
              color: "#5c3d2e",
              fontWeight: 600,
              cursor: "pointer",
              fontSize: "0.9rem",
              transition: "all 0.15s",
            }}
          >
            Hủy
          </button>
          <button
            id="redeem-confirm"
            onClick={() => onConfirm(Math.min(count, maxSelectable))}
            disabled={loading}
            style={{
              flex: 2,
              padding: "0.85rem",
              borderRadius: "0.85rem",
              border: "none",
              background: loading
                ? "#ccc"
                : "linear-gradient(135deg, #3d6b35 0%, #8cbd6e 100%)",
              color: "white",
              fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: "0.9rem",
              transition: "all 0.15s",
              boxShadow: loading ? "none" : "0 4px 16px rgba(61,107,53,0.35)",
            }}
          >
            {loading ? "Đang xử lý…" : "✅ Xác nhận đổi điểm"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Success Modal ────────────────────────────────────────────────────────────
function SuccessModal({
  codes,
  discountVnd,
  onClose,
}: {
  codes: string[];
  discountVnd: number;
  onClose: () => void;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(30,40,20,0.55)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
        padding: "1rem",
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: "1.5rem",
          padding: "2rem",
          width: "100%",
          maxWidth: "420px",
          boxShadow: "0 20px 60px rgba(61,107,53,0.25)",
          animation: "slideUp 0.25s ease-out",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🎉</div>
        <h2 style={{ color: "#3d6b35", margin: "0 0 0.5rem", fontSize: "1.3rem" }}>
          Đổi điểm thành công!
        </h2>
        <p style={{ color: "#5c3d2e", opacity: 0.7, margin: "0 0 1.5rem", fontSize: "0.9rem" }}>
          Bạn nhận được voucher giảm <strong>{formatVND(discountVnd)}</strong>
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1.5rem" }}>
          {codes.map((code) => (
            <div
              key={code}
              style={{
                background: "linear-gradient(135deg, rgba(61,107,53,0.08) 0%, rgba(140,189,110,0.12) 100%)",
                border: "1.5px dashed #8cbd6e",
                borderRadius: "0.75rem",
                padding: "0.75rem 1rem",
                fontFamily: "monospace",
                fontSize: "1rem",
                fontWeight: 700,
                color: "#3d6b35",
                letterSpacing: "0.08em",
              }}
            >
              {code}
            </div>
          ))}
        </div>

        <p style={{ color: "#5c3d2e", opacity: 0.55, fontSize: "0.75rem", margin: "0 0 1.5rem" }}>
          💡 Lưu mã và trình với nhân viên khi đến quán để được giảm giá.
        </p>

        <button
          id="success-close"
          onClick={onClose}
          style={{
            width: "100%",
            padding: "0.85rem",
            borderRadius: "0.85rem",
            border: "none",
            background: "linear-gradient(135deg, #3d6b35 0%, #8cbd6e 100%)",
            color: "white",
            fontWeight: 700,
            cursor: "pointer",
            fontSize: "0.95rem",
            boxShadow: "0 4px 16px rgba(61,107,53,0.35)",
          }}
        >
          Tuyệt vời! 🥑
        </button>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function LoyaltyPage() {
  const { user, isAuthenticated } = useAuthContext();
  const { data, loading, error, redeemPoints } = useLoyaltyContext();

  const [showRedeem, setShowRedeem] = useState(false);
  const [redeemLoading, setRedeemLoading] = useState(false);
  const [successResult, setSuccessResult] = useState<{
    codes: string[];
    discountVnd: number;
  } | null>(null);
  const [redeemError, setRedeemError] = useState<string | null>(null);

  const handleRedeem = async (count: number) => {
    setRedeemLoading(true);
    setRedeemError(null);
    try {
      const result = await redeemPoints(count);
      setShowRedeem(false);
      setSuccessResult({ codes: result.voucher_codes, discountVnd: result.discount_vnd });
    } catch (err) {
      setRedeemError(err instanceof Error ? err.message : "Lỗi khi đổi điểm.");
    } finally {
      setRedeemLoading(false);
    }
  };

  // ── Not logged in ─────────────────────────────────────────────────────────
  if (!isAuthenticated) {
    return (
      <main style={{ minHeight: "100vh", background: "#fdf6ee" }}>
        <Header />
        <div
          style={{
            maxWidth: "480px",
            margin: "0 auto",
            padding: "5rem 1rem",
            textAlign: "center",
          }}
        >
          <Image
            src="/linh-vat.png"
            alt="Linh vật Bơ Nơ Bakery"
            width={180}
            height={180}
            style={{ margin: "0 auto 1.5rem", opacity: 0.85 }}
            priority
          />
          <h1
            style={{
              fontSize: "1.6rem",
              fontWeight: 700,
              background: "linear-gradient(135deg, #3d6b35, #8cbd6e)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              marginBottom: "0.75rem",
            }}
          >
            Hệ Thống Tích Điểm
          </h1>
          <p style={{ color: "#5c3d2e", opacity: 0.7, marginBottom: "2rem" }}>
            Đăng nhập để xem và tích lũy điểm thưởng từ mỗi đơn hàng!
          </p>
          <Link
            href="/auth/login"
            style={{
              display: "inline-block",
              padding: "0.85rem 2.5rem",
              borderRadius: "9999px",
              background: "linear-gradient(135deg, #3d6b35 0%, #8cbd6e 100%)",
              color: "white",
              fontWeight: 700,
              textDecoration: "none",
              boxShadow: "0 6px 24px rgba(61,107,53,0.3)",
              fontSize: "1rem",
            }}
          >
            🔑 Đăng nhập ngay
          </Link>
        </div>
      </main>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <main style={{ minHeight: "100vh", background: "#fdf6ee" }}>
        <Header />
        <div style={{ maxWidth: "700px", margin: "3rem auto", padding: "0 1rem" }}>
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              style={{
                height: i === 1 ? "200px" : "120px",
                background: "linear-gradient(90deg, #e8f4e2 25%, #d4eccc 50%, #e8f4e2 75%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.5s infinite",
                borderRadius: "1.25rem",
                marginBottom: "1rem",
              }}
            />
          ))}
        </div>
      </main>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <main style={{ minHeight: "100vh", background: "#fdf6ee" }}>
        <Header />
        <div style={{ maxWidth: "500px", margin: "4rem auto", padding: "0 1rem", textAlign: "center" }}>
          <p style={{ color: "#e8837a", fontSize: "1rem" }}>⚠️ {error}</p>
        </div>
      </main>
    );
  }

  const pts = data?.points ?? 0;
  const availableVouchers = data?.available_vouchers ?? 0;
  const pointsToNext = data?.points_to_next_voucher ?? 0;
  const pointsPerVoucher = data?.points_per_voucher ?? 100;
  const voucherValue = data?.voucher_value ?? 5000;
  const totalEarned = data?.total_earned ?? 0;
  const transactions = data?.transactions ?? [];

  return (
    <>
      <style>{`
        @keyframes shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-10px); }
        }
      `}</style>

      <main
        style={{
          minHeight: "100vh",
          background: "linear-gradient(160deg, #f0f9eb 0%, #fdf6ee 50%, #fff5f7 100%)",
        }}
      >
        <Header />

        <div style={{ maxWidth: "720px", margin: "0 auto", padding: "2rem 1rem 4rem" }}>

          {/* ── HERO CARD ──────────────────────────────────────────────────── */}
          <div
            style={{
              background: "linear-gradient(135deg, #3d6b35 0%, #5a9447 60%, #8cbd6e 100%)",
              borderRadius: "1.75rem",
              padding: "2rem 2rem 2.5rem",
              marginBottom: "1.25rem",
              position: "relative",
              overflow: "hidden",
              boxShadow: "0 12px 40px rgba(61,107,53,0.35)",
            }}
          >
            {/* Background decoration */}
            <div
              style={{
                position: "absolute",
                top: "-40px",
                right: "-40px",
                width: "220px",
                height: "220px",
                borderRadius: "50%",
                background: "rgba(255,255,255,0.07)",
              }}
            />
            <div
              style={{
                position: "absolute",
                bottom: "-60px",
                left: "30%",
                width: "180px",
                height: "180px",
                borderRadius: "50%",
                background: "rgba(255,255,255,0.05)",
              }}
            />

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                justifyContent: "space-between",
                gap: "1rem",
                flexWrap: "wrap",
                position: "relative",
              }}
            >
              {/* Left — Points info */}
              <div>
                <p
                  style={{
                    color: "rgba(255,255,255,0.75)",
                    fontSize: "0.875rem",
                    margin: "0 0 0.25rem",
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    textTransform: "uppercase",
                  }}
                >
                  {user?.full_name || "Khách hàng"} · Điểm hiện tại
                </p>
                <h1
                  style={{
                    color: "white",
                    fontSize: "clamp(2.5rem, 8vw, 4rem)",
                    fontWeight: 800,
                    margin: "0 0 0.25rem",
                    lineHeight: 1,
                    letterSpacing: "-0.02em",
                  }}
                >
                  {pts.toLocaleString("vi-VN")}
                  <span style={{ fontSize: "1.2rem", fontWeight: 500, opacity: 0.8, marginLeft: "0.35rem" }}>
                    điểm
                  </span>
                </h1>
                <p style={{ color: "rgba(255,255,255,0.65)", fontSize: "0.8rem", margin: "0.25rem 0 0" }}>
                  Tổng tích lũy: {totalEarned.toLocaleString("vi-VN")} điểm
                </p>
              </div>

              {/* Mascot image */}
              <div style={{ animation: "float 3s ease-in-out infinite" }}>
                <Image
                  src="/linh-vat.png"
                  alt="Linh vật Bơ Nơ Bakery"
                  width={130}
                  height={130}
                  priority
                  style={{
                    filter: "drop-shadow(0 6px 16px rgba(0,0,0,0.25))",
                    userSelect: "none",
                  }}
                />
              </div>
            </div>

            {/* Progress bar */}
            <div style={{ marginTop: "1.75rem" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  color: "rgba(255,255,255,0.75)",
                  fontSize: "0.78rem",
                  marginBottom: "0.4rem",
                }}
              >
                <span>
                  {pointsToNext === 0
                    ? "✅ Bạn có thể đổi điểm ngay!"
                    : `Còn ${pointsToNext} điểm nữa để đổi voucher`}
                </span>
                <span>{availableVouchers} voucher khả dụng</span>
              </div>
              <div
                style={{
                  background: "rgba(255,255,255,0.2)",
                  borderRadius: "9999px",
                  height: "8px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    // FIX: Khi pts là bội số chính xác của pointsPerVoucher (và > 0),
                    // thanh tiến trình phải hiển thị 100% (đã sẵn sàng đổi) thay vì 0%.
                    width: `${
                      pointsToNext === 0 && pts > 0
                        ? 100
                        : ((pts % pointsPerVoucher) / pointsPerVoucher) * 100
                    }%`,
                    background: "rgba(255,255,255,0.85)",
                    borderRadius: "9999px",
                    transition: "width 1s ease-out",
                    boxShadow: "0 0 10px rgba(255,255,255,0.6)",
                  }}
                />
              </div>
            </div>
          </div>

          {/* ── INFO CARDS ─────────────────────────────────────────────────── */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: "0.85rem",
              marginBottom: "1.25rem",
            }}
          >
            {[
              { icon: "🛒", label: "Mua bánh ngọt", value: "1 điểm / 1K VND", color: "#8cbd6e" },
              { icon: "🎂", label: "Đặt bánh kem", value: "1.5 điểm / 1K VND", color: "#3d6b35" },
              { icon: "🎁", label: "Đổi điểm", value: `100 điểm = ${(voucherValue / 1000).toFixed(0)}K VND`, color: "#f4a0b5" },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  background: "white",
                  borderRadius: "1.1rem",
                  padding: "1.1rem",
                  boxShadow: "0 2px 12px rgba(61,107,53,0.08)",
                  border: `1.5px solid ${item.color}22`,
                }}
              >
                <div style={{ fontSize: "1.5rem", marginBottom: "0.4rem" }}>{item.icon}</div>
                <p
                  style={{
                    fontSize: "0.75rem",
                    color: "#5c3d2e",
                    opacity: 0.65,
                    margin: "0 0 0.25rem",
                    fontWeight: 500,
                  }}
                >
                  {item.label}
                </p>
                <p
                  style={{
                    fontSize: "0.9rem",
                    fontWeight: 700,
                    color: item.color,
                    margin: 0,
                  }}
                >
                  {item.value}
                </p>
              </div>
            ))}
          </div>

          {/* ── REDEEM BUTTON ──────────────────────────────────────────────── */}
          {availableVouchers > 0 ? (
            <button
              id="open-redeem-modal"
              onClick={() => {
                setRedeemError(null);
                setShowRedeem(true);
              }}
              style={{
                width: "100%",
                padding: "1rem",
                borderRadius: "1.1rem",
                border: "none",
                background: "linear-gradient(135deg, #3d6b35 0%, #8cbd6e 100%)",
                color: "white",
                fontWeight: 700,
                fontSize: "1rem",
                cursor: "pointer",
                boxShadow: "0 6px 24px rgba(61,107,53,0.3)",
                marginBottom: "1.25rem",
                transition: "transform 0.15s, box-shadow 0.15s",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.5rem",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-2px)";
                (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 10px 32px rgba(61,107,53,0.4)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)";
                (e.currentTarget as HTMLButtonElement).style.boxShadow = "0 6px 24px rgba(61,107,53,0.3)";
              }}
            >
              🎁 Đổi điểm lấy voucher ({availableVouchers} voucher khả dụng)
            </button>
          ) : (
            <div
              style={{
                background: "rgba(140,189,110,0.1)",
                border: "1.5px dashed #8cbd6e",
                borderRadius: "1.1rem",
                padding: "1rem",
                textAlign: "center",
                marginBottom: "1.25rem",
                color: "#3d6b35",
                fontSize: "0.9rem",
              }}
            >
              🌿 Tích thêm{" "}
              <strong>{pointsToNext > 0 ? pointsToNext : pointsPerVoucher}</strong> điểm nữa để mở khóa voucher đầu tiên!
            </div>
          )}

          {redeemError && (
            <p
              style={{
                color: "#e8837a",
                background: "#fff5f5",
                border: "1px solid #ffd0d0",
                borderRadius: "0.75rem",
                padding: "0.75rem 1rem",
                fontSize: "0.875rem",
                marginBottom: "1rem",
              }}
            >
              ⚠️ {redeemError}
            </p>
          )}

          {/* ── TRANSACTION HISTORY ────────────────────────────────────────── */}
          <div
            style={{
              background: "white",
              borderRadius: "1.25rem",
              boxShadow: "0 2px 16px rgba(61,107,53,0.09)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "1.1rem 1rem 0.85rem",
                borderBottom: "1px solid rgba(61,107,53,0.08)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <h2
                style={{
                  fontSize: "1rem",
                  fontWeight: 700,
                  color: "#3d4a35",
                  margin: 0,
                }}
              >
                📋 Lịch sử giao dịch điểm
              </h2>
              <span
                style={{
                  fontSize: "0.75rem",
                  color: "#8cbd6e",
                  fontWeight: 600,
                }}
              >
                {transactions.length} giao dịch gần nhất
              </span>
            </div>

            {transactions.length === 0 ? (
              <div
                style={{
                  padding: "3rem 1rem",
                  textAlign: "center",
                  color: "#5c3d2e",
                  opacity: 0.55,
                }}
              >
                <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🌱</div>
                <p style={{ margin: 0, fontSize: "0.9rem" }}>
                  Chưa có giao dịch nào. Hãy mua bánh để tích điểm!
                </p>
              </div>
            ) : (
              <div>
                {transactions.map((tx) => (
                  <TransactionRow key={tx.id} tx={tx} />
                ))}
              </div>
            )}
          </div>

          {/* ── HOW IT WORKS ───────────────────────────────────────────────── */}
          <div
            style={{
              marginTop: "1.25rem",
              background: "linear-gradient(135deg, rgba(61,107,53,0.06) 0%, rgba(244,160,181,0.08) 100%)",
              borderRadius: "1.1rem",
              padding: "1.25rem 1.25rem",
              border: "1px solid rgba(140,189,110,0.2)",
            }}
          >
            <h3
              style={{
                fontSize: "0.9rem",
                fontWeight: 700,
                color: "#3d6b35",
                margin: "0 0 0.75rem",
              }}
            >
              🥑 Cách tích điểm
            </h3>
            <ul
              style={{
                margin: 0,
                padding: "0 0 0 1.1rem",
                color: "#5c3d2e",
                fontSize: "0.85rem",
                lineHeight: 1.7,
                opacity: 0.8,
              }}
            >
              <li>Mua bánh ngọt tại quán → nhận <strong>1 điểm / 1,000 VND</strong></li>
              <li>Đặt bánh kem theo ý thích → nhận <strong>1.5 điểm / 1,000 VND</strong> (khi nhận bánh)</li>
              <li>Đủ 100 điểm → đổi <strong>voucher giảm 5,000 VND</strong> áp dụng tại quán</li>
            </ul>
          </div>

        </div>
      </main>

      {/* Modals */}
      {showRedeem && (
        <RedeemModal
          availableVouchers={availableVouchers}
          voucherValue={voucherValue}
          pointsPerVoucher={pointsPerVoucher}
          onClose={() => {
            setShowRedeem(false);
            setRedeemError(null);
          }}
          onConfirm={handleRedeem}
          loading={redeemLoading}
          error={redeemError}
        />
      )}

      {successResult && (
        <SuccessModal
          codes={successResult.codes}
          discountVnd={successResult.discountVnd}
          onClose={() => setSuccessResult(null)}
        />
      )}
    </>
  );
}

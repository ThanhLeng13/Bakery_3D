"use client";

/**
 * IncidentReportModal - Baker báo cáo sự cố cho một đơn hàng.
 *
 * Incident types:
 * - missing_ingredient: Thiếu nguyên liệu
 * - cannot_fulfill: Không thể thực hiện
 * - need_contact: Cần liên hệ khách hàng
 *
 * Gọi API: POST /api/v1/baker/orders/{orderId}/incident
 * Kết quả được ghi vào baker_notes để Admin thấy.
 */

import { useState } from "react";
import { apiClient, ApiError } from "@/lib/api";

type IncidentType = "missing_ingredient" | "cannot_fulfill" | "need_contact";

interface IncidentOption {
  type: IncidentType;
  label: string;
  description: string;
  icon: string;
  color: string;
}

const INCIDENT_OPTIONS: IncidentOption[] = [
  {
    type: "missing_ingredient",
    label: "Thiếu nguyên liệu",
    description: "Không đủ nguyên liệu để làm bánh theo yêu cầu",
    icon: "🧪",
    color: "border-orange-200 bg-orange-50 text-orange-800",
  },
  {
    type: "cannot_fulfill",
    label: "Không thể thực hiện",
    description: "Yêu cầu quá phức tạp hoặc thiết bị không đáp ứng được",
    icon: "⚠️",
    color: "border-red-200 bg-red-50 text-red-800",
  },
  {
    type: "need_contact",
    label: "Cần liên hệ khách hàng",
    description: "Cần xác nhận thêm thông tin từ khách trước khi tiếp tục",
    icon: "📞",
    color: "border-blue-200 bg-blue-50 text-blue-800",
  },
];

interface IncidentReportModalProps {
  orderId: string;
  orderRef: string; // Short display reference e.g. "#ABC123"
  onClose: () => void;
  onSuccess: () => void; // Called after successful report to refresh parent
}

export default function IncidentReportModal({
  orderId,
  orderRef,
  onClose,
  onSuccess,
}: IncidentReportModalProps) {
  const [selectedType, setSelectedType] = useState<IncidentType | null>(null);
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (!selectedType) {
      setError("Vui lòng chọn loại sự cố.");
      return;
    }

    setError("");
    setSubmitting(true);

    try {
      const response = await apiClient.post<{ message: string; incident_label: string }>(
        `/api/v1/baker/orders/${orderId}/incident`,
        {
          incident_type: selectedType,
          description: description.trim(),
        }
      );

      setSuccessMessage(response.message || `Đã báo cáo: ${response.incident_label}`);
      setSuccess(true);

      // Auto-close and refresh after 2 seconds
      setTimeout(() => {
        onSuccess();
        onClose();
      }, 2000);
    } catch (err: unknown) {
      const apiError = err as ApiError;
      const detail = apiError?.detail;
      setError(
        typeof detail === "string" ? detail : "Gửi báo cáo thất bại. Vui lòng thử lại."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-mocha/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="incident-modal-title"
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-gray-100">
          <div>
            <h2
              id="incident-modal-title"
              className="font-heading text-lg font-bold text-mocha"
            >
              Báo cáo sự cố
            </h2>
            <p className="text-xs text-mocha/50 mt-0.5">Đơn hàng {orderRef}</p>
          </div>
          <button
            onClick={onClose}
            className="text-mocha/50 hover:text-mocha transition-colors min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Đóng"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-5">
          {success ? (
            /* Success state */
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg
                  className="w-8 h-8 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-mocha mb-2">Đã gửi báo cáo!</h3>
              <p className="text-mocha/60 text-sm">{successMessage}</p>
              <p className="text-mocha/40 text-xs mt-2">Admin sẽ xem xét và liên hệ bạn sớm.</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Warning hint */}
              <div className="flex gap-2 p-3 bg-amber-50 border border-amber-100 rounded-xl text-xs text-amber-700">
                <span>ℹ️</span>
                <p>
                  Báo cáo sự cố sẽ được ghi vào đơn hàng và Admin sẽ thấy ngay.
                  Vui lòng chỉ báo cáo khi thực sự cần thiết.
                </p>
              </div>

              {/* Error */}
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                  {error}
                </div>
              )}

              {/* Incident type selection */}
              <div>
                <p className="text-sm font-medium text-mocha mb-2">
                  Loại sự cố <span className="text-red-500">*</span>
                </p>
                <div className="space-y-2">
                  {INCIDENT_OPTIONS.map((option) => (
                    <button
                      key={option.type}
                      type="button"
                      onClick={() => setSelectedType(option.type)}
                      className={`w-full flex items-start gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                        selectedType === option.type
                          ? `${option.color} border-current`
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <span className="text-2xl flex-shrink-0 mt-0.5">{option.icon}</span>
                      <div>
                        <p className="font-medium text-sm">{option.label}</p>
                        <p className="text-xs opacity-75 mt-0.5">{option.description}</p>
                      </div>
                      {selectedType === option.type && (
                        <svg
                          className="w-5 h-5 flex-shrink-0 ml-auto mt-0.5 text-current"
                          fill="none"
                          viewBox="0 0 24 24"
                          strokeWidth={2.5}
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Description */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label
                    htmlFor="incident-description"
                    className="text-sm font-medium text-mocha"
                  >
                    Chi tiết <span className="text-mocha/40 font-normal">(không bắt buộc)</span>
                  </label>
                  <span className={`text-xs ${description.length > 450 ? "text-red-500" : "text-mocha/40"}`}>
                    {description.length}/500
                  </span>
                </div>
                <textarea
                  id="incident-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  maxLength={500}
                  rows={3}
                  placeholder="Mô tả thêm về sự cố (vd: thiếu dâu tây, không có hộp 8 inch...)"
                  className="w-full px-4 py-3 rounded-xl border border-gray-200 text-sm text-mocha placeholder:text-mocha/40 focus:outline-none focus:ring-2 focus:ring-orange-300/50 focus:border-orange-300 resize-none"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-3 pt-1">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-3 border border-gray-200 text-mocha rounded-xl text-sm font-medium hover:bg-cream transition-colors"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  id="submit-incident-btn"
                  disabled={submitting || !selectedType}
                  className="flex-1 py-3 bg-orange-500 text-white rounded-xl text-sm font-medium hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? "Đang gửi..." : "Gửi báo cáo"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

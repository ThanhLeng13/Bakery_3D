"use client";

/**
 * StorageWarning component — displays a dismissible warning banner
 * when localStorage is unavailable or full.
 *
 * Validates: Requirements 2.10
 */

import { useState } from "react";

interface StorageWarningProps {
  /** Warning message to display */
  message: string;
}

export default function StorageWarning({ message }: StorageWarningProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between gap-3 bg-amber-50 border-b border-amber-200 px-4 py-3 shadow-sm"
    >
      <div className="flex items-center gap-2 text-sm text-amber-800">
        <svg
          width="20"
          height="20"
          viewBox="0 0 20 20"
          fill="none"
          aria-hidden="true"
          className="flex-shrink-0"
        >
          <path
            d="M10 2L1 18h18L10 2z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          <path
            d="M10 8v4M10 14h.01"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
        <span>{message}</span>
      </div>
      <button
        type="button"
        onClick={() => setDismissed(true)}
        className="flex-shrink-0 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-md text-amber-600 hover:text-amber-800 hover:bg-amber-100 transition-colors"
        aria-label="Đóng cảnh báo"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M4 4l8 8M12 4l-8 8" />
        </svg>
      </button>
    </div>
  );
}

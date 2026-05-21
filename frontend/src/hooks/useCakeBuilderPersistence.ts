"use client";

/**
 * Hook that wraps useCakeBuilder with localStorage persistence.
 * Auto-saves design state every 5 seconds and on page blur/visibility change.
 * Recovers design state from localStorage on mount.
 *
 * Validates: Requirements 2.9, 2.10
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useCakeBuilder, type UseCakeBuilderReturn } from "./useCakeBuilder";
import {
  saveCakeDesign,
  loadCakeDesign,
  clearCakeDesign,
  isLocalStorageAvailable,
} from "@/lib/cake-storage";
import type { CakeDesign } from "@/types";

/** Auto-save interval in milliseconds */
const AUTO_SAVE_INTERVAL = 5000;

export interface UseCakeBuilderPersistenceReturn extends UseCakeBuilderReturn {
  /** Warning message when localStorage is unavailable or full */
  storageWarning: string | null;
  /** Manually clear saved design from localStorage */
  clearSavedDesign: () => void;
}

export function useCakeBuilderPersistence(): UseCakeBuilderPersistenceReturn {
  // Load saved design from localStorage on initial render
  const [initialDesign] = useState<Partial<CakeDesign> | undefined>(() => {
    if (typeof window === "undefined") return undefined;
    const saved = loadCakeDesign();
    return saved ?? undefined;
  });

  const cakeBuilder = useCakeBuilder(initialDesign);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);

  // Use ref to always have access to latest design without re-triggering effects
  const designRef = useRef<CakeDesign>(cakeBuilder.design);
  designRef.current = cakeBuilder.design;

  // Check localStorage availability on mount
  useEffect(() => {
    if (!isLocalStorageAvailable()) {
      setStorageWarning(
        "Không thể lưu thiết kế tạm thời. Vui lòng hoàn thành trước khi rời trang."
      );
    }
  }, []);

  // Save function that handles errors
  const saveDesign = useCallback(() => {
    const success = saveCakeDesign(designRef.current);
    if (!success) {
      setStorageWarning(
        "Không thể lưu thiết kế tạm thời. Vui lòng hoàn thành trước khi rời trang."
      );
    }
  }, []);

  // Auto-save interval (every 5 seconds)
  useEffect(() => {
    const intervalId = setInterval(saveDesign, AUTO_SAVE_INTERVAL);
    return () => clearInterval(intervalId);
  }, [saveDesign]);

  // Save on visibility change (tab hidden) and window blur
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        saveDesign();
      }
    };

    const handleBlur = () => {
      saveDesign();
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("blur", handleBlur);

    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.removeEventListener("blur", handleBlur);
    };
  }, [saveDesign]);

  // Clear localStorage on design completion
  useEffect(() => {
    if (cakeBuilder.isComplete) {
      clearCakeDesign();
    }
  }, [cakeBuilder.isComplete]);

  const clearSavedDesign = useCallback(() => {
    clearCakeDesign();
  }, []);

  return {
    ...cakeBuilder,
    storageWarning,
    clearSavedDesign,
  };
}

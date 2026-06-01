"use client";

/**
 * CartContext - Global shopping cart state.
 *
 * Persists cart to localStorage so items survive page refreshes.
 * Exposes addItem, removeItem, updateQuantity, clearCart actions.
 *
 * Branch logic:
 * - Each CartItem carries branchId + branchName
 * - All items in a cart should be from the same branch
 * - Adding an item from a different branch triggers a window.confirm
 *   (called OUTSIDE the state updater to keep updater pure)
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useCallback,
  ReactNode,
  useMemo,
} from "react";
import type { CartItem } from "@/types";

const CART_STORAGE_KEY = "bakery_cart";

interface CartContextValue {
  items: CartItem[];
  totalItems: number;
  totalPrice: number;
  isOpen: boolean;
  /** Chi nhánh hiện tại của giỏ hàng (lấy từ item đầu tiên) */
  selectedBranchId: string | null;
  selectedBranchName: string | null;
  openCart: () => void;
  closeCart: () => void;
  addItem: (item: Omit<CartItem, "cartKey" | "quantity"> & { quantity?: number }) => void;
  removeItem: (cartKey: string) => void;
  updateQuantity: (cartKey: string, quantity: number) => void;
  clearCart: () => void;
}

const CartContext = createContext<CartContextValue | null>(null);

/** Cart key includes branch so same product from different branches = different cart slots */
function makeCartKey(productId: string, branchId: string | null): string {
  return branchId ? `${productId}__${branchId}` : productId;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Keep a ref to latest items so addItem can read it without being in dependency array
  const itemsRef = useRef<CartItem[]>([]);
  useEffect(() => {
    itemsRef.current = items;
  }, [items]);

  // Hydrate from localStorage after mount (avoid SSR mismatch)
  useEffect(() => {
    try {
      const stored = localStorage.getItem(CART_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as CartItem[];
        if (Array.isArray(parsed)) {
          setItems(parsed);
        }
      }
    } catch {
      // Corrupt data — ignore
    }
    setHydrated(true);
  }, []);

  // Persist to localStorage whenever items change (after hydration)
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    } catch {
      // Storage quota exceeded — ignore
    }
  }, [items, hydrated]);

  const totalItems = useMemo(
    () => items.reduce((sum, item) => sum + item.quantity, 0),
    [items]
  );

  const totalPrice = useMemo(
    () => items.reduce((sum, item) => sum + item.unitPrice * item.quantity, 0),
    [items]
  );

  const selectedBranchId = useMemo(
    () => (items.length > 0 ? items[0].branchId : null),
    [items]
  );

  const selectedBranchName = useMemo(
    () => (items.length > 0 ? items[0].branchName : null),
    [items]
  );

  const openCart = useCallback(() => setIsOpen(true), []);
  const closeCart = useCallback(() => setIsOpen(false), []);

  /**
   * addItem — safely adds an item to the cart.
   * Branch mismatch confirm runs OUTSIDE the state updater to keep updater pure.
   */
  const addItem = useCallback(
    (newItem: Omit<CartItem, "cartKey" | "quantity"> & { quantity?: number }) => {
      const cartKey = makeCartKey(newItem.productId, newItem.branchId ?? null);
      const qty = Math.max(1, newItem.quantity ?? 1); // guard: clamp to minimum 1

      // Read current state via ref (safe, no staleness issues for this purpose)
      const currentItems = itemsRef.current;
      const existingBranchId = currentItems.length > 0 ? (currentItems[0].branchId ?? null) : null;
      const incomingBranchId = newItem.branchId ?? null;

      // Branch mismatch — confirm BEFORE touching state (keeps updater pure)
      if (
        currentItems.length > 0 &&
        existingBranchId !== incomingBranchId
      ) {
        const existingBranchName = currentItems[0].branchName ?? "chi nhánh hiện tại";
        const newBranchName = newItem.branchName ?? "chi nhánh mới";
        const confirmed = window.confirm(
          `Giỏ hàng đang có sản phẩm từ "${existingBranchName}".\n` +
          `Bạn có muốn đổi sang "${newBranchName}" và xoá các sản phẩm cũ không?`
        );
        if (!confirmed) return;
        // Replace entire cart with just this new item
        setItems([{ ...newItem, cartKey, quantity: qty }]);
        return;
      }

      // Normal add / quantity bump — pure state updater
      setItems((prev) => {
        const existing = prev.find((i) => i.cartKey === cartKey);
        if (existing) {
          return prev.map((i) =>
            i.cartKey === cartKey ? { ...i, quantity: i.quantity + qty } : i
          );
        }
        return [...prev, { ...newItem, cartKey, quantity: qty }];
      });
    },
    []
  );

  const removeItem = useCallback((cartKey: string) => {
    setItems((prev) => prev.filter((i) => i.cartKey !== cartKey));
  }, []);

  const updateQuantity = useCallback((cartKey: string, quantity: number) => {
    if (quantity <= 0) {
      setItems((prev) => prev.filter((i) => i.cartKey !== cartKey));
    } else {
      setItems((prev) =>
        prev.map((i) => (i.cartKey === cartKey ? { ...i, quantity } : i))
      );
    }
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
    try {
      localStorage.removeItem(CART_STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return (
    <CartContext.Provider
      value={{
        items,
        totalItems,
        totalPrice,
        isOpen,
        selectedBranchId,
        selectedBranchName,
        openCart,
        closeCart,
        addItem,
        removeItem,
        updateQuantity,
        clearCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export function useCart(): CartContextValue {
  const ctx = useContext(CartContext);
  if (!ctx) {
    // Return safe no-op fallback when used outside CartProvider (e.g. admin pages)
    return {
      items: [],
      totalItems: 0,
      totalPrice: 0,
      isOpen: false,
      selectedBranchId: null,
      selectedBranchName: null,
      openCart: () => {},
      closeCart: () => {},
      addItem: () => {},
      removeItem: () => {},
      updateQuantity: () => {},
      clearCart: () => {},
    };
  }
  return ctx;
}

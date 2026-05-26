"use client";

/**
 * AuthContext - Global auth state shared across the entire app.
 * Fixes the issue where Header doesn't update after login/register
 * without a page reload.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import {
  AuthUser,
  LoginData,
  RegisterData,
  getStoredUser,
  isAuthenticated as checkAuth,
  login as authLogin,
  register as authRegister,
  logout as authLogout,
  startAutoRefresh,
  stopAutoRefresh,
  refreshToken,
  isTokenExpiringSoon,
} from "@/lib/auth";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Init user đồng bộ từ localStorage (dùng stored user ngay, validate async sau)
  const [user, setUser] = useState<AuthUser | null>(() => {
    if (typeof window === "undefined") return null;
    // Trả về stored user ngay cả khi token chưa kiểm tra — async effect sẽ validate
    return getStoredUser();
  });
  // loading = true cho đến khi async validate xong
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedUser = getStoredUser();

      if (!storedUser) {
        // Không có user nào trong localStorage → chắc chắn chưa đăng nhập
        setUser(null);
        setLoading(false);
        return;
      }

      if (checkAuth()) {
        // Access token còn hạn
        setUser(storedUser);
        if (isTokenExpiringSoon(5)) {
          // Sắp hết hạn → refresh ngay
          const result = await refreshToken();
          if (result) setUser(result.user);
          // Nếu refresh fail, giữ nguyên user (token vẫn còn một chút hạn)
        }
        startAutoRefresh();
      } else {
        // Access token hết hạn → thử refresh bằng refresh_token
        const result = await refreshToken();
        if (result) {
          // Refresh thành công → vẫn đăng nhập
          setUser(result.user);
          startAutoRefresh();
        } else {
          // Refresh thất bại → phiên hết hạn, đăng xuất
          setUser(null);
        }
      }

      setLoading(false);
    };

    initAuth();

    // Lắng nghe thay đổi auth từ tab khác
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "auth_user") {
        if (e.newValue) {
          try { setUser(JSON.parse(e.newValue)); }
          catch { setUser(null); }
        } else {
          setUser(null);
        }
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => {
      stopAutoRefresh();
      window.removeEventListener("storage", handleStorage);
    };
  }, []);

  const login = useCallback(async (data: LoginData) => {
    const response = await authLogin(data);
    setUser(response.user);
    startAutoRefresh();
  }, []);

  const register = useCallback(async (data: RegisterData) => {
    const response = await authRegister(data);
    setUser(response.user);
    startAutoRefresh();
  }, []);

  const logout = useCallback(async () => {
    await authLogout();
    stopAutoRefresh();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used inside <AuthProvider>");
  }
  return ctx;
}

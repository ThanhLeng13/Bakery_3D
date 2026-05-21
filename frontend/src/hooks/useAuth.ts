"use client";

/**
 * React hook for auth state management.
 * Provides user state, loading state, and auth actions (login, logout, register).
 * Starts auto-refresh on mount when authenticated.
 */

import { useState, useEffect, useCallback } from "react";
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

export interface UseAuthReturn {
  user: AuthUser | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (data: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
}

export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initAuth = async () => {
      const storedUser = getStoredUser();
      if (storedUser && checkAuth()) {
        setUser(storedUser);

        // If token is expiring soon, refresh it
        if (isTokenExpiringSoon(5)) {
          const result = await refreshToken();
          if (result) {
            setUser(result.user);
          } else {
            setUser(null);
          }
        }

        startAutoRefresh();
      } else {
        setUser(null);
      }
      setLoading(false);
    };

    initAuth();

    return () => {
      stopAutoRefresh();
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

  return {
    user,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
  };
}

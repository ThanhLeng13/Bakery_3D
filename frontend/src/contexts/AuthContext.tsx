"use client";

/**
 * AuthContext - Global auth state shared across the entire app.
 *
 * Design notes:
 * - user state initializes to null to avoid SSR/client hydration mismatch
 *   (window is undefined on server; useEffect runs only on client after hydration)
 * - storage event handler manages auto-refresh timers to prevent timer leaks
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
  /**
   * Initialize to null — NOT from localStorage.
   *
   * Reason: The server renders with window=undefined (user=null). If the client
   * immediately initializes from localStorage, the initial HTML differs between
   * server and client, causing a React hydration mismatch.
   * The useEffect below safely hydrates auth state after the client mounts.
   */
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Guard flag: prevents state updates / timer starts if this provider
    // unmounts while initAuth is still awaiting a network call (refreshToken)
    let active = true;

    const initAuth = async () => {
      try {
        const storedUser = getStoredUser();

        if (!storedUser) {
          return;
        }

        if (checkAuth()) {
          if (active) setUser(storedUser);
          if (isTokenExpiringSoon(5)) {
            const result = await refreshToken();
            if (!active) return; // component unmounted during await
            if (result) {
              setUser(result.user);
            } else {
              // Proactive refresh failed — purge stale session from localStorage
              try {
                await authLogout();
              } finally {
                setUser(null);
                stopAutoRefresh();
              }
              return;
            }
          }
          if (active) startAutoRefresh();
        } else {
          const result = await refreshToken();
          if (!active) return; // component unmounted during await
          if (result) {
            setUser(result.user);
            startAutoRefresh();
          } else {
            // Silent refresh failed — purge stale session from localStorage
            try {
              await authLogout();
            } finally {
              setUser(null);
            }
          }
        }
      } catch (err) {
        console.error("Auth initialization failed:", err);
        // Fallback: clear user state on error to prevent broken states
        if (active) {
          setUser(null);
          stopAutoRefresh();
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    initAuth();

    /**
     * Handle auth changes from other tabs via the storage event.
     * Also manages auto-refresh timers to avoid leaks:
     * - On login in another tab  → start auto-refresh here too
     * - On logout in another tab → stop auto-refresh here to prevent stale timers
     */
    const handleStorage = (e: StorageEvent) => {
      if (e.key === "auth_user") {
        if (e.newValue) {
          try {
            setUser(JSON.parse(e.newValue));
            startAutoRefresh(); // New session started in another tab
          } catch {
            setUser(null);
            stopAutoRefresh();
          }
        } else {
          // auth_user removed → logged out in another tab
          setUser(null);
          stopAutoRefresh();
        }
      }
    };

    window.addEventListener("storage", handleStorage);

    return () => {
      active = false; // cancel any in-flight initAuth state updates
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
    try {
      await authLogout();
    } finally {
      stopAutoRefresh();
      setUser(null);
    }
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

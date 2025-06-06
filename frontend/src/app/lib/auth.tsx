//src/app/lib/auth.ts
"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  ReactNode,
} from "react";
import {
  loginApi,
  logoutUserApi,
  getMeApi,
  refreshTokenApi,
} from "./api";
import type { AuthResponse, UserRead } from "./types";

export interface AuthContextValue {
  user: UserRead | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

// 👇 Алиас для совместимости с useAuthReturn/UseAuthReturn
export type UseAuthReturn = AuthContextValue;

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserRead | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const storeTokens = (tokens: AuthResponse) => {
    localStorage.setItem("access_token", tokens.access_token);
    if (tokens.refresh_token) {
      localStorage.setItem("refresh_token", tokens.refresh_token);
    }
  };

  const clearTokens = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  };

  const fetchUser = useCallback(
    async (accessToken: string): Promise<boolean> => {
      try {
        const userData = await getMeApi(accessToken);
        setUser(userData);
        setIsAuthenticated(true);
        localStorage.setItem("user", JSON.stringify(userData));
        return true;
      } catch (err) {
        setUser(null);
        setIsAuthenticated(false);
        clearTokens();
        return false;
      }
    },
    []
  );

  const refresh = useCallback(async () => {
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) throw new Error("No refresh token");
    try {
      const refreshed = await refreshTokenApi({ refresh_token: refreshToken });
      storeTokens(refreshed);
      await fetchUser(refreshed.access_token);
    } catch (err) {
      clearTokens();
      setUser(null);
      setIsAuthenticated(false);
      if (typeof window !== "undefined") window.location.href = "/auth/login";
      throw err;
    }
  }, [fetchUser]);

  useEffect(() => {
    const initAuth = async () => {
      setIsLoading(true);
      const accessToken = localStorage.getItem("access_token");
      const refreshToken = localStorage.getItem("refresh_token");
      if (accessToken) {
        const ok = await fetchUser(accessToken);
        if (!ok && refreshToken) {
          try {
            await refresh();
          } catch { /* already handled */ }
        }
      } else if (refreshToken) {
        try {
          await refresh();
        } catch { /* already handled */ }
      } else {
        setUser(null);
        setIsAuthenticated(false);
        clearTokens();
      }
      setIsLoading(false);
    };
    initAuth();
  }, [fetchUser, refresh]);

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    try {
      const resp = await loginApi(username, password);
      storeTokens(resp);
      if (resp.user) {
        setUser(resp.user);
        setIsAuthenticated(true);
        localStorage.setItem("user", JSON.stringify(resp.user));
      } else {
        await fetchUser(resp.access_token);
      }
      setIsLoading(false);
      return true;
    } catch (err) {
      setIsLoading(false);
      clearTokens();
      setUser(null);
      setIsAuthenticated(false);
      throw err;
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await logoutUserApi();
    } catch {
      // ignore
    }
    clearTokens();
    setUser(null);
    setIsAuthenticated(false);
    setIsLoading(false);
    if (typeof window !== "undefined") window.location.href = "/auth/login";
  };

  const value: AuthContextValue = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refresh,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Кастомный хук для удобства использования
export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};

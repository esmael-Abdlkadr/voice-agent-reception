"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearStoredToken, getStoredToken, storeToken } from "@/lib/api";
import type { AuthUser } from "@/lib/types";

type AuthStatus = "checking" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
    setStatus("anonymous");
  }, []);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setStatus("anonymous");
      return;
    }
    api
      .me()
      .then((currentUser) => {
        setUser(currentUser);
        setStatus("authenticated");
      })
      .catch(() => logout());
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api.login(email, password);
    storeToken(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
  }, []);

  const value = useMemo(() => ({ status, user, login, logout }), [status, user, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

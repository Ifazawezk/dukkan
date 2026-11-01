import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, getToken, setToken } from "../api/client";
import type { Role, TokenOut, User } from "../api/types";

interface Auth {
  user: User | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
  hasRole: (...roles: Role[]) => boolean;
}

const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  // Restore the session from a saved token.
  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    window.addEventListener("dukkan:unauthorized", logout);
    return () => window.removeEventListener("dukkan:unauthorized", logout);
  }, [logout]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api<TokenOut>("/auth/login", { form: { username, password } });
    setToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const value = useMemo<Auth>(
    () => ({
      user,
      ready,
      login,
      logout,
      hasRole: (...roles) => (user ? roles.includes(user.role) : false),
    }),
    [user, ready, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): Auth {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

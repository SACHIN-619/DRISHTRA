import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, getToken, setToken, setUnauthorizedHandler } from "./api";

export type Role = "ML_ANALYST" | "SECURITY_ANALYST" | "REVIEWER_SUPERVISOR" | "AUDITOR" | "ADMINISTRATOR";
export interface User {
  user_id: string; username: string; full_name: string; role: Role; access_scope: string;
  must_change_password: boolean; permissions: string[]; is_demo_account: boolean;
  capabilities: { title: string; mission: string; question: string; explicitly_forbidden: string[] };
}

interface AuthCtx {
  user: User | null; ready: boolean;
  login: (u: string, p: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setSession: (token: string, user: User) => void;
  can: (perm: string) => boolean;
}
const Ctx = createContext<AuthCtx>(null as any);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    if (!getToken()) { setUser(null); setReady(true); return; }
    try { setUser(await api<User>("/api/v1/auth/me")); } catch { setToken(null); setUser(null); }
    setReady(true);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => { setToken(null); setUser(null); window.location.hash = "/login"; });
    refresh();
  }, [refresh]);

  const login = async (username: string, password: string) => {
    const r = await api<{ access_token: string; user: User }>("/api/v1/auth/token", { body: { username, password } });
    setToken(r.access_token); setUser(r.user); return r.user;
  };
  const logout = async () => {
    try { await api("/api/v1/auth/logout", { method: "POST" }); } catch { /* ignore */ }
    setToken(null); setUser(null); window.location.hash = "/";
  };
  const setSession = (token: string, u: User) => { setToken(token); setUser(u); };
  const can = (perm: string) => !!user?.permissions?.includes(perm);
  return <Ctx.Provider value={{ user, ready, login, logout, refresh, setSession, can }}>{children}</Ctx.Provider>;
}

export const ROLE_LABEL: Record<Role, string> = {
  ML_ANALYST: "ML Analyst",
  SECURITY_ANALYST: "Security Analyst",
  REVIEWER_SUPERVISOR: "Reviewer / Supervisor",
  AUDITOR: "Auditor",
  ADMINISTRATOR: "Administrator",
};

export const ROLE_HOME: Record<Role, string> = {
  ML_ANALYST: "/ml",
  SECURITY_ANALYST: "/security",
  REVIEWER_SUPERVISOR: "/review",
  AUDITOR: "/audit",
  ADMINISTRATOR: "/admin",
};

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { api, clearStoredToken, getStoredToken, storeToken } from "@/lib/api";
import type { AuthUser, WorkspaceRole, WorkspaceSummary } from "@/lib/types";

type AuthStatus = "checking" | "authenticated" | "anonymous";

type AuthContextValue = {
  status: AuthStatus;
  user: AuthUser | null;
  workspaces: WorkspaceSummary[];
  currentWorkspaceId: number | null;
  setCurrentWorkspaceId: (id: number | null) => void;
  currentRole: WorkspaceRole | null;
  canEdit: boolean;
  hasAccess: (minRole: WorkspaceRole) => boolean;
  newWorkspaceModalOpen: boolean;
  openNewWorkspaceModal: () => void;
  closeNewWorkspaceModal: () => void;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const WORKSPACE_KEY = "voiceops_current_workspace_id";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [currentWorkspaceId, setCurrentWorkspaceIdState] = useState<number | null>(null);
  const [newWorkspaceModalOpen, setNewWorkspaceModalOpen] = useState(false);

  const setCurrentWorkspaceId = useCallback((id: number | null) => {
    setCurrentWorkspaceIdState(id);
    if (typeof window !== "undefined") {
      if (id === null) window.localStorage.removeItem(WORKSPACE_KEY);
      else window.localStorage.setItem(WORKSPACE_KEY, String(id));
    }
  }, []);

  const openNewWorkspaceModal = useCallback(() => {
    setNewWorkspaceModalOpen(true);
  }, []);
  const closeNewWorkspaceModal = useCallback(() => {
    setNewWorkspaceModalOpen(false);
  }, []);

  const logout = useCallback(() => {
    clearStoredToken();
    setUser(null);
    setWorkspaces([]);
    setCurrentWorkspaceId(null);
    setStatus("anonymous");
  }, [setCurrentWorkspaceId]);

  const applyContext = useCallback(
    (ctx: { user: AuthUser; workspaces: WorkspaceSummary[] }) => {
      setUser(ctx.user);
      setWorkspaces(ctx.workspaces);
      let next: number | null = null;
      if (typeof window !== "undefined") {
        const stored = window.localStorage.getItem(WORKSPACE_KEY);
        if (stored && ctx.workspaces.some((w) => w.id === Number(stored))) {
          next = Number(stored);
        }
      }
      if (next === null && ctx.workspaces.length > 0) {
        next = ctx.workspaces[0].id;
      }
      setCurrentWorkspaceId(next);
      setStatus("authenticated");
    },
    [setCurrentWorkspaceId]
  );

  const refresh = useCallback(async () => {
    const ctx = await api.me();
    applyContext(ctx);
  }, [applyContext]);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setStatus("anonymous");
      return;
    }
    refresh().catch(() => logout());
  }, [logout, refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.login(email, password);
      storeToken(response.access_token);
      const ctx = await api.me();
      applyContext(ctx);
    },
    [applyContext]
  );

  const currentRole: WorkspaceRole | null =
    workspaces.find((w) => w.id === currentWorkspaceId)?.role ?? null;
  const ROLE_RANK: Record<WorkspaceRole, number> = { viewer: 1, admin: 2, owner: 3 };
  const hasAccess = useCallback(
    (minRole: WorkspaceRole) => {
      if (user?.is_superuser) return true;
      if (!currentRole) return false;
      return ROLE_RANK[currentRole] >= ROLE_RANK[minRole];
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [user?.is_superuser, currentRole]
  );
  const canEdit = hasAccess("admin");

  const value = useMemo(
    () => ({
      status,
      user,
      workspaces,
      currentWorkspaceId,
      setCurrentWorkspaceId,
      currentRole,
      canEdit,
      hasAccess,
      newWorkspaceModalOpen,
      openNewWorkspaceModal,
      closeNewWorkspaceModal,
      login,
      logout,
      refresh,
    }),
    [
      status,
      user,
      workspaces,
      currentWorkspaceId,
      setCurrentWorkspaceId,
      currentRole,
      canEdit,
      hasAccess,
      newWorkspaceModalOpen,
      openNewWorkspaceModal,
      closeNewWorkspaceModal,
      login,
      logout,
      refresh,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

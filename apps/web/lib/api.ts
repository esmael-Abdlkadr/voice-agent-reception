import type {
  Agent,
  AgentCreate,
  AgentUpdate,
  CallDetail,
  CallSummary,
  CurrentUserContext,
  KnowledgeDoc,
  KnowledgeSearchResponse,
  LiveKitTokenResponse,
  LoginResponse,
  Tool,
  ToolCreate,
  ToolTestResponse,
  ToolUpdate,
  WorkspaceAnalytics,
  WorkspaceDetail,
  WorkspaceMember,
  WorkspaceSummary,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const AUTH_TOKEN_KEY = "voiceops_token";

export function getStoredToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(AUTH_TOKEN_KEY) ?? "";
}

export function storeToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getStoredToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    if (response.status === 401) clearStoredToken();
    const body = await response.text().catch(() => "");
    throw new Error(`API ${response.status}: ${body || response.statusText}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  // Auth
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<CurrentUserContext>("/auth/me"),

  // Workspaces
  listWorkspaces: () => request<WorkspaceSummary[]>("/workspaces"),
  createWorkspace: (payload: { name: string; slug?: string }) =>
    request<WorkspaceDetail>("/workspaces", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getWorkspace: (id: number) => request<WorkspaceDetail>(`/workspaces/${id}`),
  updateWorkspace: (id: number, payload: { name?: string; slug?: string }) =>
    request<WorkspaceDetail>(`/workspaces/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteWorkspace: (id: number) =>
    request<void>(`/workspaces/${id}`, { method: "DELETE" }),
  listMembers: (workspaceId: number) =>
    request<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`),

  // Agents
  listAgents: (workspaceId: number) =>
    request<Agent[]>(`/workspaces/${workspaceId}/agents`),
  createAgent: (workspaceId: number, payload: AgentCreate) =>
    request<Agent>(`/workspaces/${workspaceId}/agents`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateAgent: (workspaceId: number, agentId: number, payload: AgentUpdate) =>
    request<Agent>(`/workspaces/${workspaceId}/agents/${agentId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteAgent: (workspaceId: number, agentId: number) =>
    request<void>(`/workspaces/${workspaceId}/agents/${agentId}`, {
      method: "DELETE",
    }),

  // Knowledge
  listKnowledge: (workspaceId: number) =>
    request<KnowledgeDoc[]>(`/workspaces/${workspaceId}/knowledge`),
  uploadKnowledge: async (workspaceId: number, file: File) => {
    const token = getStoredToken();
    const form = new FormData();
    form.append("file", file);
    const response = await fetch(
      `${API_BASE_URL}/workspaces/${workspaceId}/knowledge`,
      {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        body: form,
        cache: "no-store",
      }
    );
    if (!response.ok) {
      if (response.status === 401) clearStoredToken();
      const body = await response.text().catch(() => "");
      throw new Error(`API ${response.status}: ${body || response.statusText}`);
    }
    return (await response.json()) as KnowledgeDoc;
  },
  getKnowledge: (workspaceId: number, docId: number) =>
    request<KnowledgeDoc>(`/workspaces/${workspaceId}/knowledge/${docId}`),
  deleteKnowledge: (workspaceId: number, docId: number) =>
    request<void>(`/workspaces/${workspaceId}/knowledge/${docId}`, {
      method: "DELETE",
    }),
  searchKnowledge: (workspaceId: number, query: string, limit = 5) =>
    request<KnowledgeSearchResponse>(
      `/workspaces/${workspaceId}/knowledge/search`,
      {
        method: "POST",
        body: JSON.stringify({ query, limit }),
      }
    ),

  // Calls
  listCalls: (workspaceId: number) =>
    request<CallSummary[]>(`/workspaces/${workspaceId}/calls`),
  getCall: (workspaceId: number, callId: number) =>
    request<CallDetail>(`/workspaces/${workspaceId}/calls/${callId}`),

  // Tools
  listTools: (workspaceId: number) =>
    request<Tool[]>(`/workspaces/${workspaceId}/tools`),
  createTool: (workspaceId: number, payload: ToolCreate) =>
    request<Tool>(`/workspaces/${workspaceId}/tools`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateTool: (workspaceId: number, toolId: number, payload: ToolUpdate) =>
    request<Tool>(`/workspaces/${workspaceId}/tools/${toolId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteTool: (workspaceId: number, toolId: number) =>
    request<void>(`/workspaces/${workspaceId}/tools/${toolId}`, {
      method: "DELETE",
    }),
  testTool: (workspaceId: number, toolId: number, query: string) =>
    request<ToolTestResponse>(
      `/workspaces/${workspaceId}/tools/${toolId}/test`,
      {
        method: "POST",
        body: JSON.stringify({ query }),
      }
    ),

  // Analytics
  workspaceAnalytics: (workspaceId: number, days = 30) =>
    request<WorkspaceAnalytics>(
      `/workspaces/${workspaceId}/analytics?days=${days}`
    ),

  // LiveKit
  livekitToken: (params: {
    workspace_id: number;
    agent_id?: number;
    identity?: string;
  }) =>
    request<LiveKitTokenResponse>("/livekit/token", {
      method: "POST",
      body: JSON.stringify(params),
    }),
};

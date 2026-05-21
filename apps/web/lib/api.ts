import type { Appointment, AuthUser, CallSession, Campaign, Contact, KnowledgeDocument, LoginResponse, MetricOverview, TwilioSetupStatus } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const AUTH_TOKEN_KEY = "voiceagentos_token";

export function getStoredToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(AUTH_TOKEN_KEY) ?? "";
}

export function storeToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearStoredToken() {
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
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) =>
    request<LoginResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<AuthUser>("/auth/me"),
  overview: () => request<MetricOverview>("/analytics/overview"),
  calls: () => request<CallSession[]>("/calls"),
  appointments: () => request<Appointment[]>("/appointments"),
  contacts: () => request<Contact[]>("/contacts"),
  campaigns: () => request<Campaign[]>("/campaigns"),
  knowledge: () => request<KnowledgeDocument[]>("/knowledge/documents"),
  twilioSetup: () => request<TwilioSetupStatus>("/twilio/setup"),
  createSession: () => request<CallSession>("/agent/session", { method: "POST", body: JSON.stringify({ direction: "inbound" }) }),
  sendMessage: (sessionId: string, message: string) =>
    request<{ reply: string; outcome: string }>("/agent/message", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    }),
  startCampaign: (campaignId: string) =>
    request<{ created_calls: number; outcomes: string[] }>(`/campaigns/${campaignId}/start-simulation`, { method: "POST" }),
  searchKnowledge: (query: string) =>
    request<{ results: Array<{ title: string; content: string }> }>("/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    }),
};

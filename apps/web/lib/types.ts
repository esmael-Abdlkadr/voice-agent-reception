export type AuthUser = {
  id: number;
  email: string;
  name: string;
  status: string;
  is_superuser: boolean;
  created_at: string;
};

export type WorkspaceRole = "owner" | "admin" | "viewer";

export type PhoneNumber = {
  id: number;
  e164: string;
  label: string;
  provider: string;
  workspace_id: number;
  agent_id: number | null;
  is_active: boolean;
  created_at: string;
};

export type PhoneNumberCreate = {
  e164: string;
  label?: string;
  agent_id?: number | null;
};

export type PhoneNumberUpdate = {
  label?: string;
  agent_id?: number | null;
  is_active?: boolean;
};

export type Reservation = {
  id: number;
  workspace_id: number;
  guest_name: string;
  guest_phone: string | null;
  check_in: string;
  check_out: string;
  room_type: string;
  num_guests: number;
  notes: string;
  status: "requested" | "confirmed" | "cancelled";
  call_id: number | null;
  created_at: string;
};

export type WorkspaceSummary = {
  id: number;
  slug: string;
  name: string;
  role: WorkspaceRole;
};

export type WorkspaceDetail = {
  id: number;
  slug: string;
  name: string;
  created_at: string;
  created_by_user_id: number;
};

export type WorkspaceMember = {
  id: number;
  user_id: number;
  role: WorkspaceRole;
  created_at: string;
  user_email: string;
  user_name: string;
};

export type Agent = {
  id: number;
  workspace_id: number;
  name: string;
  persona_prompt: string;
  greeting: string;
  voice_id: string;
  voice_provider: string;
  llm_model: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AgentCreate = {
  name: string;
  persona_prompt?: string;
  greeting?: string;
  voice_id?: string;
  voice_provider?: string;
  llm_model?: string;
  is_active?: boolean;
};

export type AgentUpdate = Partial<AgentCreate>;

export type CallStatus = "active" | "completed" | "failed" | "escalated";
export type CallTurnRole = "user" | "agent";

export type CallSummary = {
  id: number;
  workspace_id: number;
  agent_id: number | null;
  livekit_room_id: string;
  caller_identity: string;
  started_at: string;
  ended_at: string | null;
  status: CallStatus;
  outcome: string | null;
  duration_ms: number | null;
};

export type CallTurn = {
  id: number;
  role: CallTurnRole;
  text: string;
  ts_ms: number;
  audio_ms: number | null;
};

export type CallToolCall = {
  id: number;
  tool_name: string;
  args_json: Record<string, unknown>;
  result_json: Record<string, unknown>;
  ts_ms: number;
  duration_ms: number;
  status: string;
};

export type CallDetail = CallSummary & {
  escalation_reason: string | null;
  recording_url: string | null;
  turns: CallTurn[];
  tool_calls: CallToolCall[];
};

export type Tool = {
  id: number;
  workspace_id: number;
  name: string;
  description: string;
  webhook_url: string;
  auth_header: string | null;
  schema_json: Record<string, unknown>;
  created_at: string;
};

export type ToolCreate = {
  name: string;
  description: string;
  webhook_url: string;
  auth_header?: string | null;
  schema_json?: Record<string, unknown>;
};

export type ToolUpdate = Partial<ToolCreate>;

export type ToolTestResponse = {
  status_code: number;
  response_body: string;
  error: string | null;
  duration_ms: number;
};

export type KnowledgeStatus = "processing" | "ready" | "failed";

export type KnowledgeDoc = {
  id: number;
  workspace_id: number;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: KnowledgeStatus;
  chunk_count: number;
  created_at: string;
};

export type KnowledgeSearchHit = {
  doc_id: number;
  filename: string;
  chunk_idx: number;
  text: string;
  score: number;
};

export type KnowledgeSearchResponse = {
  query: string;
  hits: KnowledgeSearchHit[];
};

export type CurrentUserContext = {
  user: AuthUser;
  workspaces: WorkspaceSummary[];
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type LiveKitTokenResponse = {
  token: string;
  url: string;
  room: string;
  identity: string;
  workspace_id: number;
  agent_id: number | null;
};

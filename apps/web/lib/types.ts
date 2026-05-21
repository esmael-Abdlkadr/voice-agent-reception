export type MetricOverview = {
  total_calls: number;
  appointments_booked: number;
  campaigns: number;
  contacts: number;
  rag_questions_answered: number;
  estimated_local_platform_cost: string;
  top_outcomes: Record<string, number>;
};

export type CallMessage = {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type CallSession = {
  id: string;
  contact_name: string;
  direction: "inbound" | "outbound";
  status: string;
  outcome: string;
  summary: string;
  provider?: string;
  external_call_id?: string;
  caller_number?: string;
  called_number?: string;
  provider_status?: string;
  duration_seconds?: number;
  messages: CallMessage[];
};

export type Appointment = {
  id: string;
  contact_name: string;
  title: string;
  starts_at: string;
  status: string;
  notes: string;
};

export type Contact = {
  id: string;
  name: string;
  phone: string;
  email: string;
  company: string;
  source: string;
};

export type Campaign = {
  id: string;
  name: string;
  mode: string;
  prompt?: string;
  status: string;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  content: string;
  source_name: string;
};

export type UserRole = "platform_admin" | "campaign_operator" | "analyst";

export type AuthUser = {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  status: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type TwilioSetupStatus = {
  account_sid_configured: boolean;
  auth_token_configured: boolean;
  phone_number_configured: boolean;
  public_webhook_base_url: string;
  validate_webhooks: boolean;
  inbound_webhook_url: string;
  gather_webhook_url: string;
  status_callback_url: string;
  recording_callback_url: string;
};

import type { Appointment, CallSession, Campaign, Contact, KnowledgeDocument, MetricOverview } from "./types";

export const fallbackOverview: MetricOverview = {
  total_calls: 18,
  appointments_booked: 7,
  campaigns: 2,
  contacts: 42,
  rag_questions_answered: 13,
  estimated_local_platform_cost: "$0",
  top_outcomes: {
    appointment_booked: 7,
    callback_requested: 5,
    not_interested: 4,
    voicemail_simulated: 2,
  },
};

export const fallbackCalls: CallSession[] = [
  {
    id: "call_demo_001",
    contact_name: "Lina",
    direction: "inbound",
    status: "completed",
    outcome: "appointment_booked",
    summary: "Lina booked a cleaning for Tuesday morning.",
    messages: [
      { id: "m1", session_id: "call_demo_001", role: "user", content: "I need a cleaning next Tuesday morning.", created_at: "" },
      { id: "m2", session_id: "call_demo_001", role: "assistant", content: "I booked Tuesday 10:00 AM at BrightCare Dental.", created_at: "" },
    ],
  },
];

export const fallbackAppointments: Appointment[] = [
  {
    id: "appt_demo_001",
    contact_name: "Lina",
    title: "Dental cleaning",
    starts_at: "Tuesday 10:00 AM",
    status: "booked",
    notes: "Booked by AI receptionist.",
  },
];

export const fallbackContacts: Contact[] = [
  { id: "contact_001", name: "Amara Johnson", phone: "555-0112", email: "amara@example.com", company: "BrightCare Dental", source: "seed" },
  { id: "contact_002", name: "Daniel Reed", phone: "555-0144", email: "daniel@example.com", company: "BrightCare Dental", source: "seed" },
];

export const fallbackCampaigns: Campaign[] = [
  { id: "campaign_001", name: "Whitening Follow-up", mode: "outbound", status: "draft" },
];

export const fallbackKnowledge: KnowledgeDocument[] = [
  {
    id: "doc_001",
    title: "BrightCare Dental FAQ",
    source_name: "seed",
    content: "Open Monday-Friday, whitening consultations start at $149, emergency appointments are available.",
  },
];

export function outcomeLabel(outcome: string) {
  return outcome.replaceAll("_", " ");
}

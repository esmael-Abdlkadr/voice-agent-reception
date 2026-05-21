import type { Appointment, CallSession, Campaign, Contact, KnowledgeDocument } from "./types";

const internalQaPattern = /\bcurl\b|created by curl suite|curl suite updated|sip_0033/i;

export function outcomeLabel(outcome: string) {
  const labels: Record<string, string> = {
    appointment_booked: "appointment booked",
    appointment_requested: "appointment requested",
    callback_requested: "callback requested",
    voicemail_simulated: "voicemail",
    in_progress: "in progress",
    no_answer: "no answer",
    not_interested: "not interested",
  };

  return labels[outcome] ?? outcome.replaceAll("_", " ");
}

export function isInternalQaText(...values: Array<string | undefined | null>) {
  return values.some((value) => internalQaPattern.test(value ?? ""));
}

export function visibleCalls(calls: CallSession[]) {
  return calls.filter(
    (call) =>
      call.contact_name.toLowerCase() !== "unknown caller" &&
      call.outcome !== "in_progress" &&
      !isInternalQaText(
        call.id,
        call.contact_name,
        call.summary,
        call.messages.map((message) => message.content).join(" "),
      ),
  );
}

export function visibleAppointments(appointments: Appointment[]) {
  return appointments.filter((appointment) => !isInternalQaText(appointment.contact_name, appointment.notes, appointment.title));
}

export function visibleContacts(contacts: Contact[]) {
  return contacts.filter((contact) => !isInternalQaText(contact.name, contact.email, contact.source));
}

export function visibleCampaigns(campaigns: Campaign[]) {
  return campaigns.filter((campaign) => !isInternalQaText(campaign.name, campaign.prompt));
}

export function visibleKnowledgeDocuments(documents: KnowledgeDocument[]) {
  return documents.filter((document) => !isInternalQaText(document.title, document.source_name, document.content));
}

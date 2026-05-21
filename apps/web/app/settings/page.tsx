import { AppShell } from "@/components/app-shell";
import { DataPanel } from "@/components/data-panel";
import { PageHeader } from "@/components/page-header";
import { api } from "@/lib/api";
import type { TwilioSetupStatus } from "@/lib/types";

const settings = [
  ["Agent mode", "Groq-powered AI replies"],
  ["Voice mode", "Browser speech plus Twilio inbound phone"],
  ["LLM", "Groq llama-3.1-8b-instant"],
  ["Knowledge", "Local search with Groq answer synthesis"],
  ["Telephony", "Twilio TwiML Gather with SIP-ready upgrade path"],
];

const fallbackTwilio: TwilioSetupStatus = {
  account_sid_configured: false,
  auth_token_configured: false,
  phone_number_configured: false,
  public_webhook_base_url: "",
  validate_webhooks: false,
  inbound_webhook_url: "/twilio/voice/inbound",
  gather_webhook_url: "/twilio/voice/gather",
  status_callback_url: "/twilio/voice/status",
  recording_callback_url: "/twilio/voice/recording",
};

function ConfigPill({ ready, label }: { ready: boolean; label: string }) {
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-black ${ready ? "bg-mint text-moss" : "bg-coral/[0.12] text-coral"}`}>
      {label}: {ready ? "configured" : "missing"}
    </span>
  );
}

export default async function SettingsPage() {
  const twilio = await api.twilioSetup().catch(() => fallbackTwilio);

  return (
    <AppShell>
      <PageHeader eyebrow="Runtime configuration" title="Assistant, voice, knowledge, and telephony settings." description="Review the active AI provider, browser voice workflow, Twilio inbound phone setup, and production telephony path." />
      <div className="grid gap-5">
        <DataPanel title="Runtime settings">
          <div className="grid gap-3 md:grid-cols-2">
            {settings.map(([label, value]) => (
              <div key={label} className="rounded-md border border-line bg-cloud/[0.70] p-4">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink/45">{label}</p>
                <p className="mt-2 font-black text-ink">{value}</p>
              </div>
            ))}
          </div>
        </DataPanel>

        <DataPanel title="Twilio inbound phone setup">
          <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
            <div className="rounded-2xl border border-line bg-cloud/[0.70] p-4">
              <p className="text-sm font-black text-ink">Webhook URLs</p>
              <div className="mt-3 grid gap-2 text-sm">
                <code className="rounded-lg bg-white px-3 py-2 text-ink/[0.72]">Inbound: {twilio.inbound_webhook_url}</code>
                <code className="rounded-lg bg-white px-3 py-2 text-ink/[0.72]">Status: {twilio.status_callback_url}</code>
                <code className="rounded-lg bg-white px-3 py-2 text-ink/[0.72]">Gather: {twilio.gather_webhook_url}</code>
              </div>
              <p className="mt-4 text-sm leading-6 text-ink/[0.62]">
                For local testing, run <code className="rounded bg-white px-1.5 py-1 font-bold">ngrok http 8000</code>, copy the HTTPS URL into <code className="rounded bg-white px-1.5 py-1 font-bold">PUBLIC_WEBHOOK_BASE_URL</code>, then paste the inbound URL into your Twilio phone number Voice webhook.
              </p>
            </div>
            <aside className="rounded-2xl border border-line bg-white p-4">
              <p className="text-sm font-black text-ink">Configuration status</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <ConfigPill ready={twilio.account_sid_configured} label="Account SID" />
                <ConfigPill ready={twilio.auth_token_configured} label="Auth token" />
                <ConfigPill ready={twilio.phone_number_configured} label="Phone number" />
              </div>
              <div className="mt-4 rounded-xl bg-ink px-3 py-3 text-sm leading-6 text-white/[0.72]">
                Webhook validation is <strong className="text-white">{twilio.validate_webhooks ? "enabled" : "disabled"}</strong>. Keep it disabled for first local ngrok tests, then enable it for production-like verification.
              </div>
            </aside>
          </div>
        </DataPanel>
      </div>
    </AppShell>
  );
}

import { AgentPlayground } from "@/components/agent-playground";
import { AppShell } from "@/components/app-shell";
import { PageHeader } from "@/components/page-header";

export default function PlaygroundPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Browser voice and typed fallback"
        title="Run the AI receptionist live."
        description="Speak or type a caller request, let the assistant book an appointment, then review the saved call in the dashboard."
      />
      <AgentPlayground />
    </AppShell>
  );
}

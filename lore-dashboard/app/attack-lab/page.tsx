import {AppShell} from "@/components/app-shell";
import {AttackLabClient} from "@/components/AttackLabClient";

export default function AttackLabPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Attack Lab</h1>
          <p className="mt-1 text-sm text-slate-600">Probe semantic guardrails with prompt-injection and memory-exfiltration attempts.</p>
        </div>
        <AttackLabClient />
      </div>
    </AppShell>
  );
}

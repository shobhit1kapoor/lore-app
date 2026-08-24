import {AppShell} from "@/components/app-shell";
import {AttackLabClient} from "@/components/AttackLabClient";

export default function AttackLabPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Attack Lab</h1>
          <p className="mt-1 max-w-3xl text-sm text-zinc-400">Run prompt injection, memory exfiltration, encoded leakage, tool abuse, cross-project retrieval, malicious-MR, and log-injection probes. Every result links to its evidence receipt.</p>
        </div>
        <AttackLabClient />
      </div>
    </AppShell>
  );
}

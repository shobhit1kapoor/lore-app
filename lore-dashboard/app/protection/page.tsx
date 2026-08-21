import {AppShell} from "@/components/app-shell";
import {ProtectionDemo} from "@/components/ProtectionDemo";

export default function ProtectionPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Protection Lab</h1>
          <p className="mt-1 text-sm text-zinc-400">Run data discovery, tokenization, and masking against text before it reaches the AI model or memory.</p>
        </div>
        <ProtectionDemo />
      </div>
    </AppShell>
  );
}

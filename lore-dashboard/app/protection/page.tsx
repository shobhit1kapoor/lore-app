import {AppShell} from "@/components/app-shell";
import {ProtectionDemo} from "@/components/ProtectionDemo";

export default function ProtectionPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Protection Lab</h1>
          <p className="mt-1 max-w-3xl text-sm text-zinc-400">Run the real isolated Protegrity boundary: Data Discovery, full canonical protection, pseudonymization, post-protection rescan, and a hash-chained receipt before memory or model access.</p>
        </div>
        <ProtectionDemo />
      </div>
    </AppShell>
  );
}

import {AppShell} from "@/components/app-shell";
import {TraceTimeline} from "@/components/TraceTimeline";
import {getTrace} from "@/lib/api";

export default async function TraceDetailPage({params}: {params: Promise<{id: string}>}) {
  const {id} = await params;
  const trace = await getTrace(id);
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="break-all text-2xl font-semibold text-ink">{id}</h1>
          <p className="mt-1 text-sm text-zinc-400">Ordered Protection Receipt with policy decisions, destination evidence, latency, and cryptographic chain hashes. No source payloads are stored here.</p>
        </div>
        <TraceTimeline events={trace.events} />
      </div>
    </AppShell>
  );
}

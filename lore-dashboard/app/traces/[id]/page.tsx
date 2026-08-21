import {AppShell} from "@/components/app-shell";
import {TraceTimeline} from "@/components/TraceTimeline";
import {getTrace} from "@/lib/api";

export default async function TraceDetailPage({params}: {params: {id: string}}) {
  const trace = await getTrace(params.id);
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="break-all text-2xl font-semibold text-ink">{params.id}</h1>
          <p className="mt-1 text-sm text-zinc-400">Ordered protection and agent timeline.</p>
        </div>
        <TraceTimeline events={trace.events} />
      </div>
    </AppShell>
  );
}

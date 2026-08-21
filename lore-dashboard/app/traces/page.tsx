import {AppShell} from "@/components/app-shell";
import {RiskBadge} from "@/components/RiskBadge";
import {getTraces} from "@/lib/api";

export default async function TracesPage() {
  const traces = await getTraces();
  return (
    <AppShell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-ink">Traces</h1>
          <p className="mt-1 text-sm text-zinc-400">Every agent, tool, AI, memory, and protection event grouped by trace ID.</p>
        </div>
        <div className="border border-line bg-[#111111]">
          {traces.length ? traces.map((trace) => (
            <a key={trace.trace_id} href={`/traces/${trace.trace_id}`} className="grid gap-4 border-b border-line p-4 last:border-b-0 hover:bg-panel lg:grid-cols-[1fr_160px_120px]">
              <div>
                <div className="font-mono text-sm font-semibold text-ink">{trace.trace_id}</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {trace.event_types.slice(0, 6).map((type) => <span key={type} className="bg-panel px-2 py-1 text-xs text-zinc-300">{type}</span>)}
                </div>
              </div>
              <div className="text-sm text-zinc-400">{trace.event_count} events</div>
              <RiskBadge blocked={trace.blocked} score={trace.max_risk_score} />
            </a>
          )) : <div className="p-6 text-sm text-zinc-500">No traces recorded yet.</div>}
        </div>
      </div>
    </AppShell>
  );
}

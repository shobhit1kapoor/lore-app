import {RiskBadge} from "./RiskBadge";
import type {TelemetryEvent} from "../lib/types";

export function TraceTimeline({events}: {events: TelemetryEvent[]}) {
  if (!events.length) {
    return <div className="border border-dashed border-line bg-[#111111] p-6 text-sm text-zinc-500">No events recorded yet.</div>;
  }
  return (
    <div className="space-y-3">
      {events.map((event) => (
        <div key={event.event_id} className="border border-line bg-[#111111] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="font-semibold text-ink">{event.event_type}</div>
              <div className="text-sm text-zinc-500">{event.source || "unknown"} to {event.destination || "unknown"} · {event.timestamp}</div>
            </div>
            <RiskBadge blocked={event.policy_result === "blocked" || event.event_type.endsWith("_BLOCKED")} score={event.risk_score || 0} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(event.data_categories || []).map((category) => (
              <span key={category} className="border border-line bg-panel px-2 py-1 text-xs text-zinc-300">{category}</span>
            ))}
          </div>
          <div className="mt-4 grid gap-px bg-white/10 sm:grid-cols-2 lg:grid-cols-4">
            <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Policy</div><div className="mt-1 text-xs text-zinc-200">{event.policy_result || "recorded"}</div></div>
            <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Action</div><div className="mt-1 text-xs text-zinc-200">{event.protection_action || event.tool_name || "evidence"}</div></div>
            <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Latency</div><div className="mt-1 text-xs text-zinc-200">{event.latency_ms == null ? "—" : `${event.latency_ms} ms`}</div></div>
            <div className="bg-[#111111] p-3"><div className="text-[10px] uppercase tracking-[0.12em] text-zinc-600">Event hash</div><div className="mt-1 truncate font-mono text-[11px] text-emerald-400" title={event.event_hash || ""}>{event.event_hash || "legacy event"}</div></div>
          </div>
          {event.metadata && Object.keys(event.metadata).length ? <div className="mt-3 grid gap-2 sm:grid-cols-2">{Object.entries(event.metadata).map(([key, value]) => <div key={key} className="flex min-w-0 items-start justify-between gap-3 border border-white/10 px-3 py-2"><span className="text-[11px] text-zinc-600">{key.replaceAll("_", " ")}</span><span className="max-w-[65%] break-all text-right font-mono text-[11px] text-zinc-300">{typeof value === "object" ? JSON.stringify(value) : String(value)}</span></div>)}</div> : null}
        </div>
      ))}
    </div>
  );
}

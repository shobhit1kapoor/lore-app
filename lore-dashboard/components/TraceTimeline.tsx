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
        </div>
      ))}
    </div>
  );
}

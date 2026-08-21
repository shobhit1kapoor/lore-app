import type {MemoryRecord, Overview, ProtectionResponse, TelemetryEvent, TraceSummary} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function getJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${path}`, {cache: "no-store"});
    if (!response.ok) return fallback;
    return (await response.json()) as T;
  } catch {
    return fallback;
  }
}

export async function getOverview(): Promise<Overview> {
  return getJson<Overview>("/api/security/overview", {
    event_count: 0,
    trace_count: 0,
    blocked_count: 0,
    tokenized_count: 0,
    masked_count: 0,
    sensitive_discovery_count: 0,
    event_counts: {},
    category_counts: {},
    recent_traces: []
  });
}

export async function getTraces(): Promise<TraceSummary[]> {
  const payload = await getJson<{traces: TraceSummary[]}>("/api/traces", {traces: []});
  return payload.traces;
}

export async function getTrace(traceId: string): Promise<{summary: TraceSummary | null; events: TelemetryEvent[]}> {
  return getJson(`/api/traces/${traceId}`, {summary: null, events: []});
}

export async function getEvents(): Promise<TelemetryEvent[]> {
  const payload = await getJson<{events: TelemetryEvent[]}>("/api/security/events?limit=200", {events: []});
  return payload.events;
}

export async function getMemories(): Promise<{memories: MemoryRecord[]; source: string; message?: string}> {
  return getJson("/api/memories", {memories: [], source: "unavailable"});
}

export async function postDemo(path: "/api/demo/protect" | "/api/demo/attack", text: string): Promise<ProtectionResponse> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {"content-type": "application/json"},
    body: JSON.stringify({text})
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return (await response.json()) as ProtectionResponse;
}

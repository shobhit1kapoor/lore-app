"""
Lightweight AgentSight-style telemetry for LORE.

Events are JSONL by default and intentionally store metadata about actions, not
raw prompts, diffs, secrets, or tool outputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import uuid
from typing import Any


class EventType(str, Enum):
    AGENT_STARTED = "AGENT_STARTED"
    AGENT_FINISHED = "AGENT_FINISHED"
    LLM_CALLED = "LLM_CALLED"
    LLM_COMPLETED = "LLM_COMPLETED"
    LLM_FAILED = "LLM_FAILED"
    MEMORY_READ = "MEMORY_READ"
    MEMORY_WRITE = "MEMORY_WRITE"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    SENSITIVE_DATA_DISCOVERED = "SENSITIVE_DATA_DISCOVERED"
    DATA_MASKED = "DATA_MASKED"
    DATA_TOKENIZED = "DATA_TOKENIZED"
    PROTECTION_FAILED = "PROTECTION_FAILED"
    UNPROTECT_REQUESTED = "UNPROTECT_REQUESTED"
    UNPROTECT_ALLOWED = "UNPROTECT_ALLOWED"
    UNPROTECT_DENIED = "UNPROTECT_DENIED"
    PROMPT_BLOCKED = "PROMPT_BLOCKED"
    OUTPUT_BLOCKED = "OUTPUT_BLOCKED"


_SENSITIVE_METADATA_KEYS = {
    "prompt",
    "user_message",
    "system_prompt",
    "diff",
    "raw",
    "raw_output",
    "tool_output",
    "response",
    "token",
    "secret",
    "password",
    "api_key",
    "authorization",
}


def new_trace_id() -> str:
    return str(uuid.uuid4())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in (metadata or {}).items():
        key_str = str(key)
        lowered = key_str.lower()
        if lowered.endswith(("_chars", "_count", "_ms")):
            safe[key_str] = value
            continue
        if any(marker in lowered for marker in _SENSITIVE_METADATA_KEYS):
            safe[key_str] = "[redacted]"
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key_str] = value if not isinstance(value, str) else value[:500]
        elif isinstance(value, list):
            safe[key_str] = [str(item)[:200] for item in value[:20]]
        elif isinstance(value, dict):
            safe[key_str] = _safe_metadata(value)
        else:
            safe[key_str] = str(value)[:500]
    return safe


@dataclass
class TelemetryEvent:
    event_type: str
    trace_id: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_utc_now)
    agent_id: str | None = None
    agent_name: str | None = None
    source: str | None = None
    destination: str | None = None
    resource: str | None = None
    tool_name: str | None = None
    data_categories: list[str] = field(default_factory=list)
    protection_action: str | None = None
    policy_result: str | None = None
    risk_score: float | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["metadata"] = _safe_metadata(self.metadata)
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True)


class JSONLTelemetrySink:
    """Append-only JSONL event sink."""

    def __init__(self, path: str | Path | None = None) -> None:
        default_path = Path(__file__).resolve().parent.parent / "logs" / "lore_events.jsonl"
        self.path = Path(path or os.environ.get("LORE_TELEMETRY_PATH", default_path))

    def emit(self, event: TelemetryEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(event.to_json() + "\n")


class TelemetryRecorder:
    """Small helper for creating and recording structured events."""

    def __init__(self, sink: JSONLTelemetrySink | None = None, enabled: bool = True) -> None:
        self.sink = sink or JSONLTelemetrySink()
        self.enabled = enabled

    def emit(
        self,
        event_type: EventType | str,
        trace_id: str,
        **kwargs: Any,
    ) -> TelemetryEvent:
        event = TelemetryEvent(
            event_type=event_type.value if isinstance(event_type, EventType) else str(event_type),
            trace_id=trace_id,
            **kwargs,
        )
        if self.enabled:
            self.sink.emit(event)
        return event


_DEFAULT_RECORDER: TelemetryRecorder | None = None


def get_default_recorder() -> TelemetryRecorder:
    global _DEFAULT_RECORDER
    if _DEFAULT_RECORDER is None:
        _DEFAULT_RECORDER = TelemetryRecorder()
    return _DEFAULT_RECORDER


def read_events(path: str | Path | None = None, limit: int | None = None) -> list[dict[str, Any]]:
    """Read telemetry JSONL events newest-last, skipping malformed lines."""
    sink = JSONLTelemetrySink(path)
    if not sink.path.exists():
        return []
    events: list[dict[str, Any]] = []
    with sink.path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    if limit is not None and limit > 0:
        return events[-limit:]
    return events


def list_traces(limit: int = 50, path: str | Path | None = None) -> list[dict[str, Any]]:
    """Return trace summaries sorted by last event timestamp descending."""
    by_trace: dict[str, dict[str, Any]] = {}
    for event in read_events(path):
        trace_id = str(event.get("trace_id") or "")
        if not trace_id:
            continue
        summary = by_trace.setdefault(
            trace_id,
            {
                "trace_id": trace_id,
                "event_count": 0,
                "started_at": event.get("timestamp"),
                "last_event_at": event.get("timestamp"),
                "agents": set(),
                "event_types": set(),
                "data_categories": set(),
                "blocked": False,
                "max_risk_score": 0.0,
            },
        )
        summary["event_count"] += 1
        summary["last_event_at"] = event.get("timestamp") or summary["last_event_at"]
        if event.get("agent_name"):
            summary["agents"].add(event["agent_name"])
        if event.get("event_type"):
            summary["event_types"].add(event["event_type"])
        for category in event.get("data_categories") or []:
            summary["data_categories"].add(category)
        if event.get("policy_result") == "blocked" or str(event.get("event_type", "")).endswith("_BLOCKED"):
            summary["blocked"] = True
        if event.get("risk_score") is not None:
            summary["max_risk_score"] = max(summary["max_risk_score"], float(event["risk_score"]))
    traces = []
    for summary in by_trace.values():
        traces.append(
            {
                **summary,
                "agents": sorted(summary["agents"]),
                "event_types": sorted(summary["event_types"]),
                "data_categories": sorted(summary["data_categories"]),
            }
        )
    traces.sort(key=lambda item: str(item.get("last_event_at") or ""), reverse=True)
    return traces[:limit]


def get_trace(trace_id: str, path: str | Path | None = None) -> dict[str, Any] | None:
    """Return a single trace with its ordered events."""
    events = [event for event in read_events(path) if event.get("trace_id") == trace_id]
    if not events:
        return None
    summary = next((trace for trace in list_traces(path=path) if trace["trace_id"] == trace_id), None)
    return {"summary": summary, "events": events}


def security_overview(path: str | Path | None = None) -> dict[str, Any]:
    """Aggregate dashboard metrics from telemetry events."""
    events = read_events(path)
    traces = list_traces(path=path)
    counts: dict[str, int] = {}
    categories: dict[str, int] = {}
    blocked_count = 0
    for event in events:
        event_type = str(event.get("event_type") or "UNKNOWN")
        counts[event_type] = counts.get(event_type, 0) + 1
        if event.get("policy_result") == "blocked" or event_type.endswith("_BLOCKED"):
            blocked_count += 1
        for category in event.get("data_categories") or []:
            categories[str(category)] = categories.get(str(category), 0) + 1
    return {
        "event_count": len(events),
        "trace_count": len(traces),
        "blocked_count": blocked_count,
        "tokenized_count": counts.get(EventType.DATA_TOKENIZED.value, 0),
        "masked_count": counts.get(EventType.DATA_MASKED.value, 0),
        "sensitive_discovery_count": counts.get(EventType.SENSITIVE_DATA_DISCOVERED.value, 0),
        "event_counts": counts,
        "category_counts": categories,
        "recent_traces": traces[:10],
    }

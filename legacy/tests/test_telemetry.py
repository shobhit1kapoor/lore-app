import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.telemetry import EventType, JSONLTelemetrySink, TelemetryRecorder, new_trace_id, verify_event_chain


def test_telemetry_event_creation_and_trace_propagation(tmp_path):
    path = tmp_path / "events.jsonl"
    recorder = TelemetryRecorder(JSONLTelemetrySink(path))
    trace_id = new_trace_id()

    event = recorder.emit(
        EventType.AGENT_STARTED,
        trace_id,
        agent_id="guardkeeper",
        metadata={"stage": "test"},
    )

    uuid.UUID(event.event_id)
    uuid.UUID(event.trace_id)
    assert event.trace_id == trace_id
    row = json.loads(path.read_text().strip())
    assert row["trace_id"] == trace_id
    assert row["event_type"] == "AGENT_STARTED"
    assert row["metadata"] == {"stage": "test"}


def test_telemetry_redacts_sensitive_metadata(tmp_path):
    path = tmp_path / "events.jsonl"
    recorder = TelemetryRecorder(JSONLTelemetrySink(path))

    recorder.emit(
        EventType.LLM_CALLED,
        new_trace_id(),
        metadata={
            "prompt": "raw prompt must not be stored",
            "diff": "source code diff",
            "api_key": "abc123",
            "safe_count": 2,
        },
    )

    row = json.loads(path.read_text().strip())
    assert row["metadata"]["prompt"] == "[redacted]"
    assert row["metadata"]["diff"] == "[redacted]"
    assert row["metadata"]["api_key"] == "[redacted]"
    assert row["metadata"]["safe_count"] == 2


def test_telemetry_events_form_a_verifiable_hash_chain(tmp_path):
    path = tmp_path / "events.jsonl"
    recorder = TelemetryRecorder(JSONLTelemetrySink(path))
    trace_id = new_trace_id()

    recorder.emit(EventType.AGENT_STARTED, trace_id, metadata={"stage": "authorize"})
    recorder.emit(EventType.PROTECTION_APPLIED, trace_id, metadata={"stage": "protect"})

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["previous_hash"] == "0" * 64
    assert rows[1]["previous_hash"] == rows[0]["event_hash"]
    assert verify_event_chain(path) == {"valid": True, "checked_events": 2, "broken_event_id": None}

    rows[0]["metadata"]["stage"] = "tampered"
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert verify_event_chain(path)["valid"] is False

import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.telemetry import EventType, JSONLTelemetrySink, TelemetryRecorder, new_trace_id


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

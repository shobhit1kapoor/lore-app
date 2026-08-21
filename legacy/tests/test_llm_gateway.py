import os
import sys
from types import SimpleNamespace
from unittest.mock import Mock

os.environ.setdefault("GITLAB_TOKEN", "test-token")
os.environ.setdefault("GITLAB_PROJECT_ID", "1")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.llm_gateway import LLMGateway
from core.telemetry import EventType, TelemetryRecorder, new_trace_id


class FakeMessages:
    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(content=[SimpleNamespace(text='{"ok": true}')])


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


class CaptureSink:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event.to_dict())


def test_llm_gateway_uses_client_and_emits_events():
    sink = CaptureSink()
    recorder = TelemetryRecorder(sink)
    trace_id = new_trace_id()
    client = FakeClient()
    gateway = LLMGateway(telemetry=recorder, trace_id=trace_id, client=client)

    result = gateway.call(
        "system",
        "user",
        agent_id="guardkeeper",
        agent_name="GUARDKEEPER",
    )

    assert result == '{"ok": true}'
    assert client.messages.kwargs["messages"] == [{"role": "user", "content": "user"}]
    assert [event["event_type"] for event in sink.events] == [
        EventType.LLM_CALLED.value,
        EventType.LLM_COMPLETED.value,
    ]
    assert {event["trace_id"] for event in sink.events} == {trace_id}
    assert sink.events[0]["metadata"]["user_message_chars"] == 4
    assert "user" not in sink.events[0]["metadata"]


def test_llm_gateway_supports_openai_compatible_responses(monkeypatch):
    import core.llm_gateway as gateway_module

    monkeypatch.setattr(gateway_module, "AI_BASE_URL", "https://example.test/v1")
    monkeypatch.setattr(gateway_module, "AI_API_KEY", "test-key")
    monkeypatch.setattr(gateway_module, "LLM_MODEL", "openai/gpt-oss-120b")
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": "ready"}}]}
    response.raise_for_status.return_value = None
    client = Mock()
    client.post.return_value = response

    gateway = LLMGateway(client=client)
    gateway._provider = "openai_compatible"

    assert gateway.call("system", "user") == "ready"
    assert client.post.call_args.kwargs["json"]["model"] == "openai/gpt-oss-120b"

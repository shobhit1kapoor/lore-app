import json
import os
import sys

os.environ.setdefault("GITLAB_TOKEN", "test-token")
os.environ.setdefault("GITLAB_PROJECT_ID", "1")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.memory import MemoryStore
from core.telemetry import EventType, JSONLTelemetrySink, TelemetryRecorder, new_trace_id


class FakeGitLab:
    def __init__(self):
        self.trace_id = new_trace_id()
        self.pages = {}

    def list_wiki_pages(self):
        return list(self.pages)

    def get_wiki_page(self, slug):
        return self.pages.get(slug)

    def create_wiki_page(self, slug, title, content):
        self.pages[slug] = content

    def update_wiki_page(self, slug, content):
        self.pages[slug] = content


def test_memory_store_uses_schema_and_emits_read_write_events(tmp_path):
    path = tmp_path / "events.jsonl"
    recorder = TelemetryRecorder(JSONLTelemetrySink(path))
    trace_id = new_trace_id()
    gitlab = FakeGitLab()
    store = MemoryStore(gitlab, telemetry=recorder, trace_id=trace_id)

    slug = store.save_memory(
        {
            "source_mr_number": "42",
            "source_mr_title": "Add retry logic",
            "date": "2026-01-15",
            "governs_files": ["src/api/auth.py"],
            "decision": "Use fixed retry intervals",
            "rejected": "Exponential backoff",
            "reason": "Avoid retry storms",
            "future_implication": "No exponential backoff",
            "decided_by": ["@alice"],
            "confidence": "HIGH",
            "status": "Active",
            "security_relevant": True,
        }
    )
    loaded = store.get_memory("001")

    assert slug == "LORE-MEMORY-001"
    assert loaded["decision"] == "Use fixed retry intervals"
    assert loaded["governs_files"] == ["src/api/auth.py"]
    assert loaded["security_relevant"] is True

    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [event["event_type"] for event in events] == [
        EventType.MEMORY_WRITE.value,
        EventType.MEMORY_READ.value,
    ]
    assert {event["trace_id"] for event in events} == {trace_id}

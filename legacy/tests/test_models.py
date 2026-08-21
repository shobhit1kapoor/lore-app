import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.models import MemoryRecord


def test_memory_record_parses_existing_wiki_memory():
    content = """LORE Memory #001
Source MR: !42 — Add retry logic
Date: 2026-01-15
Governs files: src/api/auth.py, src/api/retry.py
Decision: Use fixed retry intervals
Rejected: Exponential backoff
Reason: Thundering herd at 1000+ concurrent requests
Future implication: No exponential backoff in retry logic
Decided by: @alice, @bob
Confidence: HIGH
Status: Active
"""

    record = MemoryRecord.from_wiki_markdown(content)

    assert record.id == "001"
    assert record.source_mr_number == "42"
    assert record.source_mr_title == "Add retry logic"
    assert record.governed_files == ["src/api/auth.py", "src/api/retry.py"]
    assert record.decided_by == ["@alice", "@bob"]
    assert record.protection_status == "unprotected"
    assert record.data_categories == []


def test_memory_record_serializes_optional_fields():
    record = MemoryRecord(
        id="007",
        source_mr_number="88",
        source_mr_title="Auth hardening",
        date="2026-08-14",
        governed_files=["src/auth.py"],
        decision="Use short-lived tokens",
        reason="Limits replay window",
        future_implication="Token consumers must refresh regularly",
        decided_by=["@maya"],
        carbon_impact="N/A",
        incident_type="auth",
        depends_on=["Memory #001"],
        source_type="discussion",
        security_relevant=True,
        data_categories=["credential"],
        sensitivity="high",
    )

    text = record.to_wiki_markdown()
    parsed = MemoryRecord.from_wiki_markdown(text)

    assert parsed.security_relevant is True
    assert parsed.incident_type == "auth"
    assert parsed.data_categories == ["credential"]
    assert parsed.sensitivity == "high"
    assert parsed.to_legacy_dict()["governs_files"] == ["src/auth.py"]

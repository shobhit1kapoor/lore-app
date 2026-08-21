"""
Canonical data models for LORE core concepts.

These models stay dependency-free so they can be used by tests and future
gateways without requiring GitLab, Anthropic, or runtime credentials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    if not raw or raw.upper() == "N/A":
        return []
    return [part.strip() for part in re.split(r"[,;]", raw) if part.strip()]


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    raw = str(value).strip().lower()
    if raw in {"yes", "true", "1"}:
        return True
    if raw in {"no", "false", "0"}:
        return False
    return None


def _bool_to_text(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "N/A"


@dataclass
class MemoryRecord:
    """Canonical LORE memory record.

    Legacy code still consumes dictionaries, so ``to_legacy_dict`` preserves
    the existing key names while the dataclass provides one canonical shape.
    """

    id: str = ""
    source_mr_number: str = ""
    source_mr_title: str = ""
    date: str = ""
    governed_files: list[str] = field(default_factory=list)
    decision: str = ""
    rejected: str = "N/A"
    reason: str = ""
    future_implication: str = ""
    decided_by: list[str] = field(default_factory=list)
    confidence: str = "MEDIUM"
    status: str = "Active"
    carbon_impact: str | None = None
    incident_type: str | None = None
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    source_type: str | None = None
    security_relevant: bool | None = None
    data_categories: list[str] = field(default_factory=list)
    protection_status: str = "unprotected"
    sensitivity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryRecord":
        """Build a record from either legacy snake_case or CLI title-case keys."""
        return cls(
            id=str(data.get("id", "")).strip(),
            source_mr_number=str(
                data.get("source_mr_number")
                or data.get("Source MR Number")
                or data.get("source")
                or ""
            ).strip().lstrip("!"),
            source_mr_title=str(data.get("source_mr_title") or data.get("Source MR Title") or "").strip(),
            date=str(data.get("date") or data.get("Date") or "").strip(),
            governed_files=_split_list(
                data.get("governed_files")
                or data.get("governs_files")
                or data.get("Governs files")
                or data.get("Governed files")
            ),
            decision=str(data.get("decision") or data.get("Decision") or "").strip(),
            rejected=str(data.get("rejected") or data.get("Rejected") or "N/A").strip(),
            reason=str(data.get("reason") or data.get("Reason") or "").strip(),
            future_implication=str(
                data.get("future_implication") or data.get("Future implication") or ""
            ).strip(),
            decided_by=_split_list(data.get("decided_by") or data.get("Decided by")),
            confidence=str(data.get("confidence") or data.get("Confidence") or "MEDIUM").strip(),
            status=str(data.get("status") or data.get("Status") or "Active").strip(),
            carbon_impact=data.get("carbon_impact") or data.get("Carbon impact"),
            incident_type=data.get("incident_type") or data.get("Incident type"),
            depends_on=_split_list(data.get("depends_on") or data.get("Depends on")),
            blocks=_split_list(data.get("blocks") or data.get("Blocks")),
            source_type=data.get("source_type") or data.get("Source type"),
            security_relevant=_parse_bool(data.get("security_relevant") or data.get("Security relevant")),
            data_categories=_split_list(data.get("data_categories") or data.get("Data categories")),
            protection_status=str(
                data.get("protection_status") or data.get("Protection status") or "unprotected"
            ).strip(),
            sensitivity=data.get("sensitivity") or data.get("Sensitivity"),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_wiki_markdown(cls, content: str) -> "MemoryRecord":
        """Parse existing LORE wiki memory markdown into the canonical model."""
        fields: dict[str, Any] = {}
        for raw_line in content.strip().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            header = re.match(r"^#?\s*LORE\s+Memory\s+#(\d+)", line, re.IGNORECASE)
            if header:
                fields["id"] = header.group(1)
                continue
            line = line.strip("*")
            if line.startswith("Source MR:"):
                rest = line.replace("Source MR:", "", 1).strip()
                match = re.match(r"!(\d+)\s*[—-]\s*(.*)", rest)
                if match:
                    fields["source_mr_number"] = match.group(1)
                    fields["source_mr_title"] = match.group(2).strip()
                continue
            match = re.match(r"^([A-Za-z][A-Za-z /\-]+?):\s*(.*)$", line)
            if match:
                fields[match.group(1).strip()] = match.group(2).strip()
        return cls.from_dict(fields)

    def to_legacy_dict(self) -> dict[str, Any]:
        """Return the existing runtime dictionary shape plus optional fields."""
        return {
            "id": self.id,
            "source_mr_number": self.source_mr_number,
            "source_mr_title": self.source_mr_title,
            "date": self.date,
            "governs_files": list(self.governed_files),
            "decision": self.decision,
            "rejected": self.rejected,
            "reason": self.reason,
            "future_implication": self.future_implication,
            "decided_by": list(self.decided_by),
            "confidence": self.confidence,
            "status": self.status,
            "carbon_impact": self.carbon_impact,
            "incident_type": self.incident_type,
            "depends_on": list(self.depends_on),
            "blocks": list(self.blocks),
            "source_type": self.source_type,
            "security_relevant": self.security_relevant,
            "data_categories": list(self.data_categories),
            "protection_status": self.protection_status,
            "sensitivity": self.sensitivity,
            "metadata": dict(self.metadata),
        }

    def to_wiki_markdown(self) -> str:
        """Serialize to a backwards-compatible wiki memory page."""
        lines = [
            f"LORE Memory #{self.id}",
            f"Source MR: !{self.source_mr_number} — {self.source_mr_title}",
            f"Date: {self.date}",
            f"Governs files: {', '.join(self.governed_files)}",
            f"Decision: {self.decision}",
            f"Rejected: {self.rejected}",
            f"Reason: {self.reason}",
            f"Future implication: {self.future_implication}",
            f"Decided by: {', '.join(self.decided_by)}",
            f"Confidence: {self.confidence}",
            f"Status: {self.status}",
        ]
        optional_fields = [
            ("Carbon impact", self.carbon_impact),
            ("Incident type", self.incident_type),
            ("Depends on", ", ".join(self.depends_on) if self.depends_on else None),
            ("Blocks", ", ".join(self.blocks) if self.blocks else None),
            ("Source type", self.source_type),
            ("Security relevant", _bool_to_text(self.security_relevant)),
            ("Data categories", ", ".join(self.data_categories) if self.data_categories else None),
            ("Protection status", self.protection_status),
            ("Sensitivity", self.sensitivity),
        ]
        for key, value in optional_fields:
            if value not in (None, ""):
                lines.append(f"{key}: {value}")
        return "\n".join(lines) + "\n"

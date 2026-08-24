"""
Sensitive-data protection gateway for LORE.

The gateway is intentionally adapter-shaped: agents call this module, while the
module can use Protegrity Developer Edition services when configured and a local
deterministic engine for demos/tests when those services are not available.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
import re
from typing import Any, Protocol
from urllib import request
from urllib.error import URLError
from urllib.parse import urlencode

from .models import MemoryRecord
from .telemetry import EventType, TelemetryRecorder, get_default_recorder, new_trace_id


class ProtectionBlocked(RuntimeError):
    """Raised when semantic guardrails deny prompt or output flow."""


class ProtectionGateway(Protocol):
    def inspect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        ...

    def protect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        ...

    def unprotect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        ...

    def check_output(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        ...


@dataclass(frozen=True)
class SensitiveFinding:
    category: str
    start: int
    end: int
    confidence: float = 0.9
    action: str = "tokenize"

    def to_public_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProtectionResult:
    text: str
    findings: list[SensitiveFinding]
    tokenized_count: int = 0
    masked_count: int = 0
    blocked: bool = False
    risk_score: float = 0.0
    policy_result: str = "allowed"
    reason: str | None = None
    provider: str = "local"
    fingerprint: str | None = None
    entity_counts: dict[str, int] | None = None

    @property
    def categories(self) -> list[str]:
        return sorted({finding.category for finding in self.findings})

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "findings": [finding.to_public_dict() for finding in self.findings],
            "categories": self.categories,
            "tokenized_count": self.tokenized_count,
            "masked_count": self.masked_count,
            "blocked": self.blocked,
            "risk_score": self.risk_score,
            "policy_result": self.policy_result,
            "reason": self.reason,
            "provider": self.provider,
            "fingerprint": self.fingerprint,
            "entity_counts": self.entity_counts or {},
        }


class NoOpProtectionGateway:
    """Compatibility gateway for tests or local runs that need exact passthrough."""

    def inspect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return data

    def protect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return data

    def unprotect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return data

    def check_output(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return data


class FallbackSensitiveDataEngine:
    """Deterministic discovery/protection used when Protegrity is not configured."""

    _PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
        ("EMAIL", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "tokenize"),
        ("PHONE", re.compile(r"\b(?:\+?\d[\d .-]{7,}\d)\b"), "tokenize"),
        ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "tokenize"),
        (
            "ACCOUNT_ID",
            re.compile(r"\b((?:ACCT|CUST|CUSTOMER|TENANT)-[A-Z0-9-]{4,})\b", re.I),
            "tokenize",
        ),
        (
            "ACCOUNT_ID",
            re.compile(r"\b(?:account|acct|customer|tenant)[ _-]?(?:id|number|no)?[:=# ]+([A-Z0-9-]{5,})\b", re.I),
            "tokenize",
        ),
        (
            "API_KEY",
            re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|secret|password)[:= ]+([A-Za-z0-9_\-./+=]{8,})\b", re.I),
            "mask",
        ),
        (
            "DEBUG_TOKEN",
            re.compile(r"\b(?:debug|session|bearer)[_-]?token[:= ]+([A-Za-z0-9_\-./+=]{8,})\b", re.I),
            "mask",
        ),
        (
            "PERSON",
            re.compile(r"\b(?:user|customer|owner|requester|author)[:= ]+([A-Z][a-z]+(?: [A-Z][a-z]+){1,2})\b"),
            "tokenize",
        ),
    )

    def discover(self, text: str) -> list[SensitiveFinding]:
        findings: list[SensitiveFinding] = []
        for category, pattern, action in self._PATTERNS:
            for match in pattern.finditer(text):
                start, end = match.span(1) if match.lastindex else match.span(0)
                findings.append(
                    SensitiveFinding(
                        category=category,
                        start=start,
                        end=end,
                        action=action,
                    )
                )
        findings.sort(key=lambda finding: (finding.start, -(finding.end - finding.start)))
        deduped: list[SensitiveFinding] = []
        last_end = -1
        for finding in findings:
            if finding.start < last_end:
                continue
            deduped.append(finding)
            last_end = finding.end
        return deduped

    def protect(self, text: str, findings: list[SensitiveFinding]) -> ProtectionResult:
        if not findings:
            return ProtectionResult(text=text, findings=[])

        parts: list[str] = []
        cursor = 0
        tokenized_count = 0
        masked_count = 0
        for finding in findings:
            parts.append(text[cursor : finding.start])
            raw_value = text[finding.start : finding.end]
            if finding.action == "mask":
                replacement = f"[{finding.category}_REDACTED]"
                masked_count += 1
            else:
                digest = hashlib.sha256(f"{finding.category}:{raw_value}".encode("utf-8")).hexdigest()[:10]
                replacement = f"<{finding.category}_TOKEN_{digest}>"
                tokenized_count += 1
            parts.append(replacement)
            cursor = finding.end
        parts.append(text[cursor:])
        return ProtectionResult(
            text="".join(parts),
            findings=findings,
            tokenized_count=tokenized_count,
            masked_count=masked_count,
        )


class ProtegrityDiscoveryClient:
    """Client for the local Protegrity Data Discovery text-classification API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_seconds: float = 2.0) -> None:
        configured_url = os.environ.get("PROTEGRITY_DISCOVERY_URL") if base_url is None else base_url
        self.base_url = (configured_url or "").rstrip("/")
        self.api_key = api_key or os.environ.get("DEV_EDITION_API_KEY")
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def classify_text(self, text: str) -> list[SensitiveFinding]:
        if not self.configured:
            return []
        url = self.base_url
        if not url.endswith("/classify/text"):
            url = f"{url}/pty/data-discovery/v2/classify/text"
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urlencode({'score_threshold': '0.6'})}"
        body = text.encode("utf-8")
        headers = {"content-type": "text/plain"}
        req = request.Request(url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return self._parse_findings(payload, text)

    def _parse_findings(self, payload: Any, text: str) -> list[SensitiveFinding]:
        if isinstance(payload, dict) and isinstance(payload.get("classifications"), dict):
            findings: list[SensitiveFinding] = []
            for category, matches in payload["classifications"].items():
                if not isinstance(matches, list):
                    continue
                for match in matches:
                    if not isinstance(match, dict):
                        continue
                    location = match.get("location")
                    if not isinstance(location, dict):
                        continue
                    start = location.get("start_index")
                    end = location.get("end_index")
                    if start is None or end is None:
                        continue
                    normalized = str(category).upper()
                    action = "mask" if normalized in {"API_KEY", "PASSWORD", "SECRET", "TOKEN", "DEBUG_TOKEN"} else "tokenize"
                    findings.append(
                        SensitiveFinding(
                            category=normalized,
                            start=int(start),
                            end=int(end),
                            confidence=float(match.get("score", 0.9)),
                            action=action,
                        )
                    )
            return findings

        candidates: list[Any]
        if isinstance(payload, dict):
            candidates = (
                payload.get("findings")
                or payload.get("entities")
                or payload.get("results")
                or payload.get("labels")
                or []
            )
        elif isinstance(payload, list):
            candidates = payload
        else:
            candidates = []

        findings: list[SensitiveFinding] = []
        for item in candidates:
            if not isinstance(item, dict):
                continue
            category = str(
                item.get("category")
                or item.get("label")
                or item.get("entityType")
                or item.get("dataElement")
                or "SENSITIVE"
            ).upper()
            start = item.get("start") or item.get("startOffset") or item.get("begin")
            end = item.get("end") or item.get("endOffset") or item.get("finish")
            if start is None or end is None:
                value = item.get("value") or item.get("text")
                if not isinstance(value, str) or not value:
                    continue
                pos = text.find(value)
                if pos < 0:
                    continue
                start, end = pos, pos + len(value)
            action = "mask" if category in {"API_KEY", "PASSWORD", "SECRET", "TOKEN", "DEBUG_TOKEN"} else "tokenize"
            findings.append(SensitiveFinding(category=category, start=int(start), end=int(end), action=action))
        return findings


class SemanticGuardrailClient:
    """Protegrity Semantic Guardrails client with a deterministic local fallback."""

    _LOCAL_BLOCK_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"ignore (all )?(previous|prior|system) instructions", re.I),
        re.compile(r"reveal .*?(secret|token|password|api key|system prompt)", re.I),
        re.compile(r"print .*?(memory|prompt|credentials).*?verbatim", re.I),
        re.compile(r"exfiltrat|data leak|bypass guardrail", re.I),
    )

    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout_seconds: float = 2.0) -> None:
        configured_url = os.environ.get("PROTEGRITY_GUARDRAIL_URL") if base_url is None else base_url
        self.base_url = (configured_url or "").rstrip("/")
        self.api_key = api_key or os.environ.get("DEV_EDITION_API_KEY")
        self.timeout_seconds = timeout_seconds

    def assess(self, text: str, context: dict[str, Any] | None = None) -> tuple[bool, float, str]:
        if self.base_url:
            try:
                return self._assess_remote(text, context)
            except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
                pass
        for pattern in self._LOCAL_BLOCK_PATTERNS:
            if pattern.search(text):
                return False, 0.96, "Prompt resembles instruction bypass or sensitive-data exfiltration."
        return True, 0.05, "Allowed by local guardrail policy."

    def _assess_remote(self, text: str, context: dict[str, Any] | None = None) -> tuple[bool, float, str]:
        processor = str((context or {}).get("guardrail_processor") or "customer-support")
        output = processor == "pii"
        body = json.dumps(
            {
                "messages": [
                    {
                        "from": "ai" if output else "user",
                        "to": "user" if output else "ai",
                        "content": text,
                        "processors": [processor],
                    }
                ]
            }
        ).encode("utf-8")
        headers = {"content-type": "application/json"}
        req = request.Request(self.base_url, data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        batch = payload.get("batch") if isinstance(payload, dict) else None
        if isinstance(batch, dict):
            outcome = str(batch.get("outcome", "")).lower()
            allowed = outcome not in {"rejected", "blocked", "denied"}
            risk_score = float(batch.get("score", 0.0))
            messages = payload.get("messages", [])
            processors = messages[0].get("processors", []) if messages and isinstance(messages[0], dict) else []
            explanation = processors[0].get("explanation") if processors and isinstance(processors[0], dict) else None
            reason = str(explanation or outcome or "Assessed by Protegrity Semantic Guardrails.")
            # Developer Edition's semantic model is trained for customer-service
            # conversations. Engineering prompts are commonly classified as
            # off-topic, which is not itself a security violation. Explicitly
            # allow that classification while still blocking malicious input and
            # every rejected PII output.
            if not output and outcome == "rejected" and reason.strip().lower() == "offtopic":
                allowed = True
            return allowed, risk_score, reason
        allowed = bool(payload.get("allowed", payload.get("allow", not payload.get("blocked", False))))
        risk_score = float(payload.get("risk_score", payload.get("riskScore", 0.0)))
        reason = str(payload.get("reason", payload.get("message", "Assessed by remote guardrail.")))
        return allowed, risk_score, reason


class ProtegrityPrivacyGatewayClient:
    """Client for LORE's isolated, credential-bearing Privacy Gateway."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 30.0) -> None:
        configured_url = os.environ.get("PROTEGRITY_PRIVACY_GATEWAY_URL") if base_url is None else base_url
        self.base_url = (configured_url or "").rstrip("/")
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.base_url)

    def health(self) -> dict[str, Any]:
        req = request.Request(f"{self.base_url}/health", method="GET")
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def protect_text(self, text: str, trace_id: str, purpose: str) -> ProtectionResult:
        gateway_trace_id = trace_id if 8 <= len(trace_id) <= 100 else hashlib.sha256(trace_id.encode()).hexdigest()[:32]
        body = json.dumps({"text": text, "traceId": gateway_trace_id, "purpose": purpose}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/v1/protect",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        findings = [
            SensitiveFinding(
                category=str(item["category"]),
                start=int(item["start"]),
                end=int(item["end"]),
                confidence=float(item.get("confidence", 0.9)),
                action=str(item.get("action", "tokenize")),
            )
            for item in payload.get("findings", [])
            if isinstance(item, dict)
        ]
        return ProtectionResult(
            text=str(payload["aiSafeText"]),
            findings=findings,
            tokenized_count=sum(finding.action == "tokenize" for finding in findings),
            masked_count=sum(finding.action == "mask" for finding in findings),
            policy_result="protected",
            reason=f"Protected by {payload.get('provider', 'Protegrity')} Privacy Gateway.",
            provider=str(payload.get("provider", "protegrity")),
            fingerprint=str(payload.get("fingerprint") or ""),
            entity_counts={str(key): int(value) for key, value in (payload.get("entityCounts") or {}).items()},
        )

    def assess(self, text: str, trace_id: str, purpose: str, output: bool = False) -> tuple[bool, float, str]:
        gateway_trace_id = trace_id if 8 <= len(trace_id) <= 100 else hashlib.sha256(trace_id.encode()).hexdigest()[:32]
        body = json.dumps(
            {
                "text": text,
                "traceId": gateway_trace_id,
                "purpose": purpose,
                "direction": "output" if output else "input",
            }
        ).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/v1/guardrail",
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return bool(payload["allowed"]), float(payload.get("riskScore", 0.0)), str(payload.get("reason") or "Assessed by Protegrity.")


class LoreProtectionGateway:
    """LORE protection boundary used by agents, memory, LLM calls, and demo APIs."""

    def __init__(
        self,
        telemetry: TelemetryRecorder | None = None,
        discovery_client: ProtegrityDiscoveryClient | None = None,
        guardrail_client: SemanticGuardrailClient | None = None,
        privacy_client: ProtegrityPrivacyGatewayClient | None = None,
        fallback_engine: FallbackSensitiveDataEngine | None = None,
        fail_closed: bool | None = None,
    ) -> None:
        self.telemetry = telemetry or get_default_recorder()
        self.discovery_client = discovery_client or ProtegrityDiscoveryClient()
        self.guardrail_client = guardrail_client or SemanticGuardrailClient()
        self.privacy_client = privacy_client or ProtegrityPrivacyGatewayClient()
        self.fallback_engine = fallback_engine or FallbackSensitiveDataEngine()
        self.fail_closed = (
            os.environ.get("PROTEGRITY_FAIL_CLOSED", "true").strip().lower() not in {"0", "false", "no"}
            if fail_closed is None
            else fail_closed
        )

    def inspect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return self.protect(data, context)

    def protect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return self._protect_value(data, context or {})

    def unprotect(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        trace_id = self._trace_id(context)
        self.telemetry.emit(
            EventType.UNPROTECT_DENIED,
            trace_id,
            policy_result="denied",
            metadata={"reason": "LORE does not automatically unprotect protected memory."},
        )
        raise PermissionError("Automatic unprotect is disabled for LORE demo flows.")

    def check_output(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        return self._protect_value(data, context or {}, output=True)

    def protect_text(self, text: str, context: dict[str, Any] | None = None, output: bool = False) -> ProtectionResult:
        context = {**(context or {}), "guardrail_processor": "pii" if output else "customer-support"}
        trace_id = self._trace_id(context)
        boundary = str(context.get("boundary", "unknown"))
        if self.privacy_client.configured:
            try:
                result = self.privacy_client.protect_text(text, trace_id, boundary)
            except (OSError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
                self.telemetry.emit(
                    EventType.PROTECTION_FAILED,
                    trace_id,
                    policy_result="blocked",
                    metadata={"boundary": boundary, "error_type": type(exc).__name__},
                )
                raise ProtectionBlocked("Protegrity protection failed closed.") from exc
        else:
            if self.fail_closed:
                self.telemetry.emit(
                    EventType.PROTECTION_FAILED,
                    trace_id,
                    policy_result="blocked",
                    metadata={"boundary": boundary, "stage": "protection", "error_type": "GatewayNotConfigured"},
                )
                raise ProtectionBlocked("Protegrity Privacy Gateway is required but not configured.")
            findings = self._discover(text, context)
            result = self.fallback_engine.protect(text, findings)
        findings = result.findings
        should_guardrail = output or (
            boundary in {"pre_llm", "demo_attack"} and context.get("prompt_part") != "system"
        )
        if should_guardrail:
            guardrail_text = text if output else result.text
            try:
                if self.privacy_client.configured:
                    allowed, risk_score, reason = self.privacy_client.assess(guardrail_text, trace_id, boundary, output=output)
                elif self.fail_closed:
                    raise ProtectionBlocked("Protegrity Privacy Gateway is required but not configured.")
                else:
                    allowed, risk_score, reason = self.guardrail_client.assess(guardrail_text, context)
            except (OSError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
                self.telemetry.emit(
                    EventType.PROTECTION_FAILED,
                    trace_id,
                    policy_result="blocked",
                    metadata={"boundary": boundary, "stage": "semantic_guardrail", "error_type": type(exc).__name__},
                )
                raise ProtectionBlocked("Protegrity Semantic Guardrails failed closed.") from exc
            if not allowed:
                event_type = EventType.OUTPUT_BLOCKED if output else EventType.PROMPT_BLOCKED
                self.telemetry.emit(
                    event_type,
                    trace_id,
                    policy_result="blocked",
                    risk_score=risk_score,
                    metadata={
                        "boundary": boundary,
                        "message_role": context.get("prompt_part"),
                        "reason": reason,
                        "input_chars": len(text),
                    },
                )
                raise ProtectionBlocked(reason)
        if findings:
            categories = result.categories
            self.telemetry.emit(
                EventType.SENSITIVE_DATA_DISCOVERED,
                trace_id,
                data_categories=categories,
                protection_action="discover",
                policy_result="matched",
                metadata={
                    "boundary": boundary,
                    "finding_count": len(findings),
                    "input_chars": len(text),
                },
            )
            if result.tokenized_count:
                self.telemetry.emit(
                    EventType.DATA_TOKENIZED,
                    trace_id,
                    data_categories=categories,
                    protection_action="tokenize",
                    policy_result="applied",
                    metadata={"boundary": boundary, "tokenized_count": result.tokenized_count},
                )
            if result.masked_count:
                self.telemetry.emit(
                    EventType.DATA_MASKED,
                    trace_id,
                    data_categories=categories,
                    protection_action="mask",
                    policy_result="applied",
                    metadata={"boundary": boundary, "masked_count": result.masked_count},
                )
        self.telemetry.emit(
            EventType.PROTECTION_APPLIED,
            trace_id,
            data_categories=result.categories,
            protection_action="pseudonymize",
            policy_result="protected",
            metadata={
                "boundary": boundary,
                "provider": result.provider,
                "finding_count": len(findings),
                "input_chars": len(text),
                "output_chars": len(result.text),
                "fingerprint_sha256": result.fingerprint or hashlib.sha256(text.encode()).hexdigest(),
            },
        )
        return result

    def assess_prompt(self, text: str, context: dict[str, Any] | None = None) -> ProtectionResult:
        context = {"boundary": "demo_attack", **(context or {})}
        trace_id = self._trace_id(context)
        protected = self.protect_text(text, {**context, "boundary": "attack_protection"})
        try:
            if self.privacy_client.configured:
                allowed, risk_score, reason = self.privacy_client.assess(protected.text, trace_id, str(context["boundary"]))
            elif self.fail_closed:
                raise ProtectionBlocked("Protegrity Privacy Gateway is required but not configured.")
            else:
                allowed, risk_score, reason = self.guardrail_client.assess(text, context)
        except (OSError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            self.telemetry.emit(
                EventType.PROTECTION_FAILED,
                trace_id,
                policy_result="blocked",
                metadata={"boundary": context["boundary"], "stage": "semantic_guardrail", "error_type": type(exc).__name__},
            )
            raise ProtectionBlocked("Protegrity Semantic Guardrails failed closed.") from exc
        if not allowed:
            self.telemetry.emit(
                EventType.PROMPT_BLOCKED,
                trace_id,
                policy_result="blocked",
                risk_score=risk_score,
                metadata={"boundary": context["boundary"], "reason": reason, "input_chars": len(text)},
            )
            return ProtectionResult(
                text="[PROMPT_BLOCKED]",
                findings=[],
                blocked=True,
                risk_score=risk_score,
                policy_result="blocked",
                reason=reason,
                provider="protegrity" if self.privacy_client.configured else "local",
                fingerprint=hashlib.sha256(text.encode()).hexdigest(),
            )
        return ProtectionResult(
            text=protected.text,
            findings=protected.findings,
            tokenized_count=protected.tokenized_count,
            masked_count=protected.masked_count,
            risk_score=risk_score,
            policy_result="allowed",
            reason=reason,
            provider=protected.provider,
            fingerprint=protected.fingerprint,
            entity_counts=protected.entity_counts,
        )

    def _protect_value(self, data: Any, context: dict[str, Any], output: bool = False) -> Any:
        if isinstance(data, str):
            return self.protect_text(data, context, output=output).text
        if isinstance(data, MemoryRecord):
            return replace(
                data,
                source_mr_title=self._protect_value(data.source_mr_title, context, output),
                decision=self._protect_value(data.decision, context, output),
                rejected=self._protect_value(data.rejected, context, output),
                reason=self._protect_value(data.reason, context, output),
                future_implication=self._protect_value(data.future_implication, context, output),
                metadata=self._protect_value(data.metadata, context, output),
            )
        if isinstance(data, dict):
            return {key: self._protect_value(value, context, output) for key, value in data.items()}
        if isinstance(data, list):
            return [self._protect_value(value, context, output) for value in data]
        return data

    def _discover(self, text: str, context: dict[str, Any]) -> list[SensitiveFinding]:
        trace_id = self._trace_id(context)
        remote_findings: list[SensitiveFinding] = []
        if self.discovery_client.configured:
            try:
                remote_findings = self.discovery_client.classify_text(text)
            except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
                self.telemetry.emit(
                    EventType.PROTECTION_FAILED,
                    trace_id,
                    policy_result="fallback",
                    metadata={"boundary": context.get("boundary"), "error_type": type(exc).__name__},
                )
        # Protegrity remains the primary classifier. Deterministic patterns close
        # gaps for secrets and repository-specific identifiers that are outside
        # the classifier's documented PII/PCI/PHI focus.
        candidates = remote_findings + self.fallback_engine.discover(text)
        selected: list[SensitiveFinding] = []
        for finding in sorted(
            candidates,
            key=lambda item: (item.start, -(item.end - item.start), -item.confidence),
        ):
            if not (0 <= finding.start < finding.end <= len(text)):
                continue
            if any(finding.start < existing.end and finding.end > existing.start for existing in selected):
                continue
            selected.append(finding)
        return sorted(selected, key=lambda item: item.start)

    def _trace_id(self, context: dict[str, Any] | None = None) -> str:
        return str((context or {}).get("trace_id") or new_trace_id())


_DEFAULT_GATEWAY: LoreProtectionGateway | None = None


def get_default_protection_gateway() -> LoreProtectionGateway:
    global _DEFAULT_GATEWAY
    if _DEFAULT_GATEWAY is None:
        _DEFAULT_GATEWAY = LoreProtectionGateway()
    return _DEFAULT_GATEWAY

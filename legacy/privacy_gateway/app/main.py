"""Isolated, fail-closed Protegrity protection boundary for LORE."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from functools import lru_cache
from threading import Lock
from typing import Any
from urllib import request as urlrequest
from urllib.error import URLError

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


DISCOVERY_URL = os.getenv(
    "PROTEGRITY_DISCOVERY_URL",
    "http://classification-service:8050/pty/data-discovery/v2/classify/text",
)
GUARDRAIL_URL = os.getenv(
    "PROTEGRITY_GUARDRAIL_URL",
    "http://semantic-guardrail-service:8001/pty/semantic-guardrail/v1.1/conversations/messages/scan",
)
POLICY_USER = os.getenv("PROTEGRITY_POLICY_USER", "superuser")
SCORE_THRESHOLD = float(os.getenv("PROTEGRITY_CLASSIFICATION_THRESHOLD", "0.60"))
CANONICAL_AAD = b"lore-canonical-v1"
TRACE_KEY_TTL_SECONDS = 10 * 60
_trace_keys: dict[str, tuple[bytes, str, float]] = {}
_trace_key_lock = Lock()


class ProtectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)
    trace_id: str = Field(alias="traceId", min_length=8, max_length=100)
    purpose: str = Field(min_length=2, max_length=80)

    model_config = {"populate_by_name": True}


class Finding(BaseModel):
    category: str
    start: int
    end: int
    confidence: float
    action: str


class ProtectResponse(BaseModel):
    canonical_protected: str = Field(alias="canonicalProtected")
    ai_safe_text: str = Field(alias="aiSafeText")
    fingerprint: str
    findings: list[Finding]
    entity_counts: dict[str, int] = Field(alias="entityCounts")
    provider: str
    duration_ms: int = Field(alias="durationMs")

    model_config = {"populate_by_name": True}


class GuardrailRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)
    trace_id: str = Field(alias="traceId", min_length=8, max_length=100)
    direction: str = Field(pattern="^(input|output)$")
    purpose: str = Field(min_length=2, max_length=80)

    model_config = {"populate_by_name": True}


class GuardrailResponse(BaseModel):
    allowed: bool
    risk_score: float = Field(alias="riskScore")
    reason: str
    processor: str
    provider: str
    duration_ms: int = Field(alias="durationMs")

    model_config = {"populate_by_name": True}


_DETERMINISTIC_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    ("EMAIL_ADDRESS", re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "tokenize"),
    ("IP_ADDRESS", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "tokenize"),
    ("ACCOUNT_ID", re.compile(r"\b(?:ACCT|CUST|TENANT|CUSTOMER)-[A-Z0-9-]{4,}\b", re.I), "tokenize"),
    (
        "API_KEY",
        re.compile(r"\b(?:sk|nvapi)-[A-Za-z0-9_\-]{8,}\b|\b(?:api[_ -]?key|secret|password)[:= ]+([A-Za-z0-9_\-./+=]{8,})\b", re.I),
        "mask",
    ),
    ("DEBUG_TOKEN", re.compile(r"\b(?:debug|session|bearer)[_-]?token[:= ]+([A-Za-z0-9_\-./+=]{8,})\b", re.I), "mask"),
)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _alpha_pseudonym(value: str) -> str:
    hexadecimal = hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
    letters = hexadecimal.translate(str.maketrans("0123456789abcdef", "ABCDEFGHIJKLMNOP"))
    return "-".join(letters)


def _safe_alias(category: str, digest: str) -> str:
    value = int(digest[:4], 16) % (26 * 26)
    label = f"{chr(65 + value // 26)}{chr(65 + value % 26)}"
    return f"[ENTITY {label}]"


@lru_cache(maxsize=1)
def _protegrity_module():
    try:
        import protegrity_developer_python as protegrity
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Protegrity discovery SDK is unavailable") from exc
    protegrity.configure(
        endpoint_url=DISCOVERY_URL,
        named_entity_map={
            "PERSON": "name",
            "NAME": "name",
            "EMAIL": "email",
            "EMAIL_ADDRESS": "email",
            "PHONE": "phone",
            "PHONE_NUMBER": "phone",
            "ADDRESS": "address",
            "LOCATION": "address",
            "IP_ADDRESS": "ip_address",
        },
        classification_score_threshold=SCORE_THRESHOLD,
        enable_logging=False,
        log_level="critical",
    )
    return protegrity


@lru_cache(maxsize=1)
def _protegrity_session():
    try:
        from appython import Protector

        return Protector().create_session(POLICY_USER)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Protegrity protection service is unavailable") from exc


def _session_action(action: str, value: str) -> Any:
    try:
        from appython.utils.exceptions import InvalidSessionError, ProtectError, UnprotectError
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Protegrity protection SDK is unavailable") from exc
    for attempt in range(2):
        try:
            return getattr(_protegrity_session(), action)(value, "string")
        except (InvalidSessionError, ProtectError, UnprotectError):
            _protegrity_session.cache_clear()
            if attempt:
                raise
    raise RuntimeError("Unreachable Protegrity session state")


def _discover(text: str) -> list[Finding]:
    try:
        classifications = _protegrity_module().discover(text)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Protegrity discovery failed closed") from exc

    candidates: list[Finding] = []
    for category, items in classifications.items():
        for item in items:
            location = item.get("location", {})
            start = int(location.get("start_index", -1))
            end = int(location.get("end_index", -1))
            if 0 <= start < end <= len(text):
                normalized = str(category).upper()
                action = "mask" if normalized in {"API_KEY", "PASSWORD", "SECRET", "TOKEN", "DEBUG_TOKEN"} else "tokenize"
                candidates.append(Finding(category=normalized, start=start, end=end, confidence=float(item.get("score", 0.9)), action=action))

    for category, pattern, action in _DETERMINISTIC_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span(1) if match.lastindex else match.span(0)
            candidates.append(Finding(category=category, start=start, end=end, confidence=1.0, action=action))

    selected: list[Finding] = []
    for finding in sorted(candidates, key=lambda item: (item.start, -(item.end - item.start), -item.confidence)):
        if any(finding.start < current.end and finding.end > current.start for current in selected):
            continue
        selected.append(finding)
    return sorted(selected, key=lambda item: item.start)


def _trace_key(trace_id: str) -> tuple[bytes, str]:
    now = time.monotonic()
    with _trace_key_lock:
        expired = [key for key, (_, _, expires_at) in _trace_keys.items() if expires_at <= now]
        for key in expired:
            del _trace_keys[key]
        cached = _trace_keys.get(trace_id)
        if cached:
            return cached[0], cached[1]
        trace_key = os.urandom(32)
        wrapped = str(_session_action("protect", _b64url_encode(trace_key)))
        _trace_keys[trace_id] = (trace_key, wrapped, now + TRACE_KEY_TTL_SECONDS)
        return trace_key, wrapped


def _protect_full_text(text: str, trace_id: str) -> tuple[str, bytes]:
    try:
        trace_key, wrapped = _trace_key(trace_id)
        nonce = os.urandom(12)
        ciphertext = AESGCM(trace_key).encrypt(nonce, text.encode("utf-8"), CANONICAL_AAD)
        return f"LORE1:{_b64url_encode(wrapped.encode())}:{_b64url_encode(nonce)}:{_b64url_encode(ciphertext)}", trace_key
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Protegrity protection failed closed") from exc


def _ai_safe_text(text: str, findings: list[Finding], trace_key: bytes) -> str:
    for finding in reversed(findings):
        if finding.action == "mask":
            replacement = f"[{finding.category}_REDACTED]"
        else:
            digest = hmac.new(trace_key, f"{finding.category}:{text[finding.start:finding.end]}".encode(), hashlib.sha256).hexdigest()
            replacement = _safe_alias(finding.category, digest)
        text = f"{text[:finding.start]}{replacement}{text[finding.end:]}"
    return text


def _assess_guardrail(text: str, direction: str) -> tuple[bool, float, str, str]:
    processor = "pii" if direction == "output" else "customer-support"
    payload = {
        "messages": [
            {
                "from": "ai" if direction == "output" else "user",
                "to": "user" if direction == "output" else "ai",
                "content": text,
                "processors": [processor],
            }
        ]
    }
    req = urlrequest.Request(
        GUARDRAIL_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urlrequest.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Protegrity Semantic Guardrails failed closed") from exc

    batch = result.get("batch") if isinstance(result, dict) else None
    if isinstance(batch, dict):
        outcome = str(batch.get("outcome", "")).lower()
        score = float(batch.get("score", 0.0))
        messages = result.get("messages", [])
        processors = messages[0].get("processors", []) if messages and isinstance(messages[0], dict) else []
        explanation = processors[0].get("explanation") if processors and isinstance(processors[0], dict) else None
        reason = str(explanation or outcome or "Assessed by Protegrity Semantic Guardrails.")
        allowed = outcome not in {"rejected", "blocked", "denied"}
        if direction == "input" and outcome == "rejected" and reason.strip().lower() == "offtopic":
            allowed = True
        return allowed, score, reason, processor

    allowed = bool(result.get("allowed", result.get("allow", not result.get("blocked", False))))
    score = float(result.get("risk_score", result.get("riskScore", 0.0)))
    reason = str(result.get("reason", result.get("message", "Assessed by Protegrity Semantic Guardrails.")))
    return allowed, score, reason, processor


app = FastAPI(title="LORE Privacy Gateway", docs_url=None, redoc_url=None)


@app.get("/health")
def health() -> dict[str, Any]:
    configured = all(os.getenv(name) for name in ("DEV_EDITION_EMAIL", "DEV_EDITION_PASSWORD", "DEV_EDITION_API_KEY"))
    if not configured:
        raise HTTPException(status_code=503, detail="Protegrity credentials are missing")
    _discover("LORE readiness probe")
    if not _protegrity_session().check_access("string", "protect"):
        raise HTTPException(status_code=503, detail="Protegrity protect policy is unavailable")
    return {"status": "ready", "provider": "protegrity", "isolated": True}


@app.post("/v1/protect", response_model=ProtectResponse, response_model_by_alias=True)
def protect(request: ProtectRequest) -> ProtectResponse:
    started = time.perf_counter()
    findings = _discover(request.text)
    canonical, trace_key = _protect_full_text(request.text, request.trace_id)
    ai_safe = _ai_safe_text(request.text, findings, trace_key)
    remaining = _discover(ai_safe)
    if remaining:
        categories = ", ".join(sorted({finding.category for finding in remaining}))
        raise HTTPException(status_code=422, detail=f"Post-protection discovery found: {categories}")
    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.category] = counts.get(finding.category, 0) + 1
    return ProtectResponse(
        canonicalProtected=canonical,
        aiSafeText=ai_safe,
        fingerprint=hashlib.sha256(request.text.encode()).hexdigest(),
        findings=findings,
        entityCounts=counts,
        provider="protegrity",
        durationMs=round((time.perf_counter() - started) * 1000),
    )


@app.post("/v1/guardrail", response_model=GuardrailResponse, response_model_by_alias=True)
def guardrail(request: GuardrailRequest) -> GuardrailResponse:
    started = time.perf_counter()
    allowed, score, reason, processor = _assess_guardrail(request.text, request.direction)
    return GuardrailResponse(
        allowed=allowed,
        riskScore=score,
        reason=reason,
        processor=processor,
        provider="protegrity",
        durationMs=round((time.perf_counter() - started) * 1000),
    )

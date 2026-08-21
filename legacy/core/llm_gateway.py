"""
Centralized LLM gateway for LORE.

All Anthropic/Claude calls go through this module so future protection and
observability can be applied at one boundary.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time

import httpx

from config import (
    ANTHROPIC_API_KEY,
    AI_API_KEY,
    AI_BASE_URL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    LLM_MODEL,
)
from .protection import ProtectionBlocked, ProtectionGateway, get_default_protection_gateway
from .telemetry import EventType, TelemetryRecorder, get_default_recorder, new_trace_id

logger = logging.getLogger("lore.llm_gateway")


class LLMGateway:
    """Single LORE boundary for LLM requests."""

    def __init__(
        self,
        telemetry: TelemetryRecorder | None = None,
        protection_gateway: ProtectionGateway | None = None,
        trace_id: str | None = None,
        client: object | None = None,
    ) -> None:
        self.telemetry = telemetry or get_default_recorder()
        self.protection = protection_gateway or get_default_protection_gateway()
        self.trace_id = trace_id or new_trace_id()
        if client is not None:
            self._client = client
            self._api_error_types: tuple[type[BaseException], ...] = ()
        else:
            if AI_BASE_URL and AI_API_KEY and LLM_MODEL:
                self._provider = "openai_compatible"
                self._client = httpx.Client(timeout=30.0)
                self._api_error_types = (httpx.HTTPError,)
            else:
                import anthropic

                self._provider = "anthropic"
                self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                self._api_error_types = (anthropic.APIError,)
        if client is not None:
            self._provider = "injected"

    def call(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
    ) -> str:
        tokens = max_tokens if max_tokens is not None else CLAUDE_MAX_TOKENS
        temp = temperature if temperature is not None else CLAUDE_TEMPERATURE
        try:
            protected_system = self.protection.protect(
                system_prompt,
                {"boundary": "pre_llm", "prompt_part": "system", "trace_id": self.trace_id},
            )
            protected_user = self.protection.protect(
                user_message,
                {"boundary": "pre_llm", "prompt_part": "user", "trace_id": self.trace_id},
            )
        except ProtectionBlocked as e:
            self.telemetry.emit(
                EventType.LLM_FAILED,
                self.trace_id,
                agent_id=agent_id,
                agent_name=agent_name,
                source="lore_agent",
                destination=self._provider,
                resource=LLM_MODEL,
                metadata={"error_type": type(e).__name__},
            )
            raise RuntimeError(f"LLM API call blocked by protection policy: {e}") from e

        self.telemetry.emit(
            EventType.LLM_CALLED,
            self.trace_id,
            agent_id=agent_id,
            agent_name=agent_name,
            source="lore_agent",
            destination=self._provider,
            resource=LLM_MODEL,
            metadata={
                "system_prompt_chars": len(system_prompt),
                "user_message_chars": len(user_message),
                "protected_system_prompt_chars": len(protected_system),
                "protected_user_message_chars": len(protected_user),
                "raw_sensitive_fields_to_llm": 0,
                "max_tokens": tokens,
                "temperature": temp,
            },
        )
        started = time.perf_counter()
        try:
            if self._provider == "openai_compatible":
                response = self._client.post(
                    f"{AI_BASE_URL.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {AI_API_KEY}"},
                    json={
                        "model": LLM_MODEL,
                        "max_tokens": tokens,
                        "temperature": temp,
                        "messages": [
                            {"role": "system", "content": protected_system},
                            {"role": "user", "content": protected_user},
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                choices = payload.get("choices", [])
                if not choices:
                    raise RuntimeError("OpenAI-compatible API returned no choices")
                text = str(choices[0]["message"].get("content") or "")
            else:
                response = self._client.messages.create(
                    model=LLM_MODEL,
                    max_tokens=tokens,
                    system=protected_system,
                    messages=[{"role": "user", "content": protected_user}],
                    temperature=temp,
                )
                if not response.content:
                    text = ""
                else:
                    first = response.content[0]
                    text = first.text if hasattr(first, "text") else str(first)
            latency_ms = int((time.perf_counter() - started) * 1000)
            text = self.protection.check_output(
                text,
                {"boundary": "pre_output", "destination": "agent", "trace_id": self.trace_id},
            )
            self.telemetry.emit(
                EventType.LLM_COMPLETED,
                self.trace_id,
                agent_id=agent_id,
                agent_name=agent_name,
                source=self._provider,
                destination="lore_agent",
                resource=LLM_MODEL,
                latency_ms=latency_ms,
                metadata={"response_chars": len(text)},
            )
            return text
        except self._api_error_types as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.telemetry.emit(
                EventType.LLM_FAILED,
                self.trace_id,
                agent_id=agent_id,
                agent_name=agent_name,
                source="lore_agent",
                destination=self._provider,
                resource=LLM_MODEL,
                latency_ms=latency_ms,
                metadata={"error_type": type(e).__name__},
            )
            logger.exception("LLM API error")
            raise RuntimeError(f"LLM API call failed: {e}") from e
        except Exception as e:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self.telemetry.emit(
                EventType.LLM_FAILED,
                self.trace_id,
                agent_id=agent_id,
                agent_name=agent_name,
                source="lore_agent",
                destination=self._provider,
                resource=LLM_MODEL,
                latency_ms=latency_ms,
                metadata={"error_type": type(e).__name__},
            )
            logger.exception("Unexpected error calling LLM")
            raise RuntimeError(f"LLM API call failed: {e}") from e

    def load_prompt(self, prompt_name: str) -> str:
        path = Path(__file__).resolve().parent.parent / "prompts" / f"{prompt_name}.txt"
        if not path.is_file():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")

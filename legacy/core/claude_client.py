"""
Backward-compatible Claude client wrapper.

New code should use LLMGateway directly. This class remains so existing call
sites and demos keep working while all LLM calls still pass through the single
gateway in core.llm_gateway.
"""

from __future__ import annotations

from .llm_gateway import LLMGateway
from .protection import ProtectionGateway
from .telemetry import TelemetryRecorder


class ClaudeClient:
    """Compatibility facade around LLMGateway."""

    def __init__(
        self,
        telemetry: TelemetryRecorder | None = None,
        protection_gateway: ProtectionGateway | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._gateway = LLMGateway(
            telemetry=telemetry,
            protection_gateway=protection_gateway,
            trace_id=trace_id,
        )

    @property
    def trace_id(self) -> str:
        return self._gateway.trace_id

    def call(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
    ) -> str:
        return self._gateway.call(
            system_prompt=system_prompt,
            user_message=user_message,
            max_tokens=max_tokens,
            temperature=temperature,
            agent_id=agent_id,
            agent_name=agent_name,
        )

    def load_prompt(self, prompt_name: str) -> str:
        return self._gateway.load_prompt(prompt_name)

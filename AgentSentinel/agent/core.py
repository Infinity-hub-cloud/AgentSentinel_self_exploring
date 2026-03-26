"""A small OpenAI-compatible tool-use loop."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from defenses.policy import (
    DEFAULT_POLICY,
    PolicyConfig,
    PolicyDecision,
    ProvenanceData,
    check_tool_call,
    label_data,
    label_tool_result,
)

from .tools import TOOL_FUNCTIONS, TOOL_SCHEMAS


DEFAULT_SYSTEM_PROMPT = (
    "You are a local research demo agent. Use tools only when needed. "
    "All files and emails are simulated inside the sandbox."
)


@dataclass
class AgentResult:
    output: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    steps: int = 0


class ToolUsingAgent:
    """Run a bounded chat-completions tool loop."""

    def __init__(
        self,
        client: Any | None = None,
        model: str | None = None,
        max_steps: int = 5,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        defense_enabled: bool = False,
        policy_config: PolicyConfig = DEFAULT_POLICY,
    ) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.max_steps = max_steps
        self.system_prompt = system_prompt
        self.defense_enabled = defense_enabled
        self.policy_config = policy_config
        self.client = client or self._build_client()

    @staticmethod
    def _build_client() -> Any:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for live agent execution")
        from openai import OpenAI

        return OpenAI(
            api_key=api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )

    @staticmethod
    def _message_dict(message: Any) -> dict[str, Any]:
        if hasattr(message, "model_dump"):
            return message.model_dump(exclude_none=True)
        if isinstance(message, dict):
            return message
        return {
            "role": getattr(message, "role", "assistant"),
            "content": getattr(message, "content", None),
            "tool_calls": getattr(message, "tool_calls", None),
        }

    @staticmethod
    def _call_parts(tool_call: Any) -> tuple[str, str, str]:
        function = getattr(tool_call, "function", None)
        if function is None and isinstance(tool_call, dict):
            function = tool_call["function"]
        if isinstance(function, dict):
            name = function["name"]
            arguments = function.get("arguments", "{}")
        else:
            name = function.name
            arguments = getattr(function, "arguments", "{}")
        call_id = getattr(tool_call, "id", None)
        if call_id is None and isinstance(tool_call, dict):
            call_id = tool_call["id"]
        return call_id, name, arguments

    def run(self, user_message: str) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        ]
        trace: list[dict[str, Any]] = []
        context: list[ProvenanceData] = [
            label_data(user_message, source="user", trusted=True, config=self.policy_config)
        ]

        for step in range(1, self.max_steps + 1):
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            messages.append(self._message_dict(message))
            tool_calls = getattr(message, "tool_calls", None)
            if not tool_calls:
                return AgentResult(message.content or "", trace, step)

            for tool_call in tool_calls:
                call_id, name, raw_arguments = self._call_parts(tool_call)
                arguments: dict[str, Any] = {}
                try:
                    arguments = json.loads(raw_arguments or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("tool arguments must be a JSON object")
                    trace.append(
                        {"type": "tool_call", "step": step, "name": name, "arguments": arguments}
                    )
                    decision = (
                        check_tool_call(name, arguments, context, self.policy_config)
                        if self.defense_enabled
                        else PolicyDecision(True, "Runtime defense is disabled.")
                    )
                    trace.append(
                        {
                            "type": "policy_decision",
                            "step": step,
                            "name": name,
                            "allowed": decision.allowed,
                            "reason": decision.reason,
                        }
                    )
                    if not decision.allowed:
                        result = f"Blocked by runtime policy: {decision.reason}"
                    else:
                        if name not in TOOL_FUNCTIONS:
                            raise ValueError(f"unknown tool: {name}")
                        result = TOOL_FUNCTIONS[name](**arguments)
                except Exception as exc:
                    result = f"Error: {exc}"
                provenance = label_tool_result(name, arguments, result, self.policy_config)
                context.append(provenance)
                trace.append(
                    {
                        "type": "tool_result",
                        "step": step,
                        "name": name,
                        "result": result,
                        "provenance": provenance.to_dict(),
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(provenance.to_dict(), ensure_ascii=False),
                    }
                )

        return AgentResult("Maximum tool steps reached.", trace, self.max_steps)

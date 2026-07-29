"""A small provenance-aware runtime policy."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProvenanceData:
    content: Any
    source: str
    trusted: bool
    sensitive: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


@dataclass(frozen=True)
class PolicyConfig:
    sensitive_tools: frozenset[str] = field(
        default_factory=lambda: frozenset({"write_file", "send_email"})
    )
    outbound_tools: frozenset[str] = field(default_factory=lambda: frozenset({"send_email"}))
    untrusted_sources: frozenset[str] = field(
        default_factory=lambda: frozenset({"file", "email", "tool_output"})
    )
    secret_markers: tuple[str, ...] = (
        "secret",
        "api_key",
        "api key",
        "password",
        "token",
        "credential",
    )


DEFAULT_POLICY = PolicyConfig()


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _looks_sensitive(value: Any, config: PolicyConfig) -> bool:
    text = _as_text(value).lower()
    return any(marker in text for marker in config.secret_markers)


def label_data(
    content: Any,
    source: str,
    trusted: bool,
    sensitive: bool | None = None,
    config: PolicyConfig = DEFAULT_POLICY,
) -> ProvenanceData:
    """Attach source, trust and sensitivity metadata to runtime data."""
    if source not in {"user", "file", "email", "tool_output"}:
        raise ValueError(f"unknown provenance source: {source}")
    return ProvenanceData(
        content=content,
        source=source,
        trusted=trusted,
        sensitive=_looks_sensitive(content, config) if sensitive is None else sensitive,
    )


def label_tool_result(
    tool_name: str,
    arguments: dict[str, Any],
    result: Any,
    config: PolicyConfig = DEFAULT_POLICY,
) -> ProvenanceData:
    """Label a tool result using the tool that produced it."""
    if tool_name == "read_file":
        source, trusted = "file", False
    elif tool_name == "read_email":
        source, trusted = "email", False
    else:
        source = "tool_output"
        trusted = tool_name in {"write_file", "send_email"}
    sensitive = _looks_sensitive(arguments, config) or _looks_sensitive(result, config)
    return label_data(result, source, trusted, sensitive, config)


def check_tool_call(
    tool_name: str,
    arguments: dict[str, Any],
    context: list[ProvenanceData],
    config: PolicyConfig = DEFAULT_POLICY,
) -> PolicyDecision:
    """Return an allow/deny decision before a proposed tool call executes."""
    if tool_name in config.outbound_tools and any(item.sensitive for item in context):
        return PolicyDecision(False, "Sensitive context cannot be sent through an outbound tool.")

    has_untrusted_context = any(
        not item.trusted and item.source in config.untrusted_sources for item in context
    )
    if tool_name in config.sensitive_tools and has_untrusted_context:
        return PolicyDecision(
            False,
            "Untrusted external content cannot authorize a sensitive tool operation.",
        )

    if tool_name in config.outbound_tools and _looks_sensitive(arguments, config):
        return PolicyDecision(False, "Sensitive tool arguments cannot leave through an outbound tool.")

    return PolicyDecision(True, "No configured runtime policy rule blocked this tool call.")

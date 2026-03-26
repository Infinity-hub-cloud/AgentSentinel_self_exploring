"""Local tools constrained to the project sandbox."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


SANDBOX_ROOT = Path(__file__).resolve().parent.parent / "sandbox"


def _safe_path(relative_path: str, area: str | None = None) -> Path:
    """Resolve a relative path and reject paths outside the sandbox."""
    if not isinstance(relative_path, str):
        raise TypeError("path must be a string")

    root = (SANDBOX_ROOT / area) if area else SANDBOX_ROOT
    root = root.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path must stay inside the sandbox")
    return candidate


def list_files(path: str = "") -> list[str]:
    """List files below ``sandbox/path`` using portable relative paths."""
    directory = _safe_path(path)
    if not directory.exists():
        raise FileNotFoundError(path)
    if not directory.is_dir():
        raise NotADirectoryError(path)

    return sorted(
        item.relative_to(SANDBOX_ROOT).as_posix()
        for item in directory.rglob("*")
        if item.is_file()
    )


def read_file(path: str) -> str:
    """Read a UTF-8 text file inside ``sandbox``."""
    file_path = _safe_path(path)
    if not file_path.is_file():
        raise FileNotFoundError(path)
    return file_path.read_text(encoding="utf-8")


def write_file(path: str, content: str) -> str:
    """Write UTF-8 text to a file inside ``sandbox``."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    file_path = _safe_path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path.relative_to(SANDBOX_ROOT).as_posix()


def read_email(email_id: str) -> str:
    """Read a simulated email stored under ``sandbox/emails``."""
    file_path = _safe_path(email_id, area="emails")
    if not file_path.is_file():
        raise FileNotFoundError(email_id)
    return file_path.read_text(encoding="utf-8")


def send_email(to: str, subject: str, body: str) -> str:
    """Store a simulated outgoing email under ``sandbox/emails/sent``."""
    for value, name in ((to, "to"), (subject, "subject"), (body, "body")):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    file_name = f"{timestamp}-{uuid.uuid4().hex[:8]}.json"
    relative_path = Path("sent") / file_name
    file_path = _safe_path(relative_path.as_posix(), area="emails")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(
            {"to": to, "subject": subject, "body": body},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return (Path("emails") / relative_path).as_posix()


TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "read_email": read_email,
    "send_email": send_email,
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in the local sandbox.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file in the local sandbox.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write UTF-8 text to a file in the local sandbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_email",
            "description": "Read a simulated email in sandbox/emails.",
            "parameters": {
                "type": "object",
                "properties": {"email_id": {"type": "string"}},
                "required": ["email_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Store a simulated email; never sends over a network.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]

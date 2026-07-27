import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent.core import ToolUsingAgent


@pytest.fixture
def local_tmp():
    path = Path(__file__).parent / ".agent_tmp"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


class FakeCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(name="list_files", arguments="{}"),
            )
            message = SimpleNamespace(role="assistant", content=None, tool_calls=[tool_call])
        else:
            message = SimpleNamespace(role="assistant", content="done", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakePolicyCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_call = SimpleNamespace(
                id="call-read",
                function=SimpleNamespace(
                    name="read_file", arguments='{"path": "files/instructions.txt"}'
                ),
            )
            message = SimpleNamespace(role="assistant", content=None, tool_calls=[tool_call])
        elif self.calls == 2:
            tool_call = SimpleNamespace(
                id="call-write",
                function=SimpleNamespace(
                    name="write_file",
                    arguments='{"path": "files/changed.txt", "content": "changed"}',
                ),
            )
            message = SimpleNamespace(role="assistant", content=None, tool_calls=[tool_call])
        else:
            message = SimpleNamespace(role="assistant", content="done", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeMalformedArgumentsCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            tool_calls = [
                SimpleNamespace(
                    id="call-valid",
                    function=SimpleNamespace(
                        name="read_file", arguments='{"path": "files/secret-note.txt"}'
                    ),
                ),
                SimpleNamespace(
                    id="call-malformed",
                    function=SimpleNamespace(name="list_files", arguments="{"),
                ),
            ]
            message = SimpleNamespace(role="assistant", content=None, tool_calls=tool_calls)
        else:
            message = SimpleNamespace(role="assistant", content="done", tool_calls=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def test_agent_executes_tool_and_keeps_trace(monkeypatch, local_tmp):
    from agent import tools

    monkeypatch.setattr(tools, "SANDBOX_ROOT", local_tmp)
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    result = ToolUsingAgent(client=client, max_steps=2).run("inspect")
    assert result.output == "done"
    assert result.steps == 2
    assert [item["type"] for item in result.trace] == [
        "tool_call",
        "policy_decision",
        "tool_result",
    ]
    assert result.trace[-1]["provenance"]["source"] == "tool_output"


def test_defense_on_blocks_sensitive_action_from_untrusted_file(monkeypatch, local_tmp):
    from agent import tools

    monkeypatch.setattr(tools, "SANDBOX_ROOT", local_tmp)
    tools.write_file("files/instructions.txt", "untrusted instructions")
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakePolicyCompletions()))

    result = ToolUsingAgent(client=client, max_steps=3, defense_enabled=True).run("inspect")

    decisions = [item for item in result.trace if item["type"] == "policy_decision"]
    assert decisions[-1]["allowed"] is False
    assert not (local_tmp / "files" / "changed.txt").exists()
    read_result = next(
        item for item in result.trace if item["type"] == "tool_result" and item["name"] == "read_file"
    )
    assert read_result["provenance"]["source"] == "file"
    assert read_result["provenance"]["trusted"] is False


def test_defense_off_allows_same_action(monkeypatch, local_tmp):
    from agent import tools

    monkeypatch.setattr(tools, "SANDBOX_ROOT", local_tmp)
    tools.write_file("files/instructions.txt", "untrusted instructions")
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakePolicyCompletions()))

    ToolUsingAgent(client=client, max_steps=3, defense_enabled=False).run("inspect")

    assert tools.read_file("files/changed.txt") == "changed"


def test_malformed_tool_arguments_do_not_reuse_previous_arguments(monkeypatch, local_tmp):
    from agent import tools

    monkeypatch.setattr(tools, "SANDBOX_ROOT", local_tmp)
    tools.write_file("files/secret-note.txt", "ordinary content")
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeMalformedArgumentsCompletions())
    )

    result = ToolUsingAgent(client=client, max_steps=2).run("inspect")

    malformed_result = [
        item for item in result.trace if item["type"] == "tool_result"
    ][-1]
    assert malformed_result["provenance"]["sensitive"] is False

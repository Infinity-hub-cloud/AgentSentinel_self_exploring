import shutil
from pathlib import Path

import pytest

from agent import tools


@pytest.fixture
def local_tmp():
    path = Path(__file__).parent / ".sandbox_tmp"
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir()
    yield path
    shutil.rmtree(path, ignore_errors=True)


def test_file_roundtrip_and_listing(local_tmp, monkeypatch):
    monkeypatch.setattr(tools, "SANDBOX_ROOT", local_tmp)
    assert tools.write_file("files/note.txt", "hello") == "files/note.txt"
    assert tools.read_file("files/note.txt") == "hello"
    assert tools.list_files() == ["files/note.txt"]


def test_paths_cannot_escape_sandbox(local_tmp, monkeypatch):
    sandbox_root = local_tmp / "sandbox"
    sandbox_root.mkdir()
    monkeypatch.setattr(tools, "SANDBOX_ROOT", sandbox_root)
    outside = local_tmp / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(ValueError):
        tools.read_file("../outside.txt")


def test_simulated_email_roundtrip(local_tmp, monkeypatch):
    monkeypatch.setattr(tools, "SANDBOX_ROOT", local_tmp)
    tools.write_file("emails/inbox/one.txt", "subject: hello")
    assert tools.read_email("inbox/one.txt") == "subject: hello"
    sent_path = tools.send_email("student@example.test", "Hi", "Body")
    assert sent_path.startswith("emails/sent/")
    assert '"subject": "Hi"' in tools.read_file(sent_path)

from defenses.policy import ProvenanceData, check_tool_call, label_data


def test_secret_like_content_is_marked_sensitive():
    data = label_data("API_KEY=example", source="file", trusted=False)

    assert data == ProvenanceData(
        content="API_KEY=example",
        source="file",
        trusted=False,
        sensitive=True,
    )


def test_untrusted_content_cannot_authorize_sensitive_tool():
    context = [label_data("instructions from a file", source="file", trusted=False)]

    decision = check_tool_call("write_file", {"path": "files/out.txt"}, context)

    assert decision.allowed is False
    assert "untrusted" in decision.reason.lower()


def test_sensitive_context_cannot_use_outbound_tool():
    context = [ProvenanceData("example-secret", "user", True, True)]

    decision = check_tool_call(
        "send_email",
        {"to": "student@example.test", "subject": "test", "body": "hello"},
        context,
    )

    assert decision.allowed is False
    assert "sensitive" in decision.reason.lower()


def test_benign_read_is_allowed():
    context = [label_data("normal task", source="user", trusted=True)]

    decision = check_tool_call("read_file", {"path": "files/note.txt"}, context)

    assert decision.allowed is True

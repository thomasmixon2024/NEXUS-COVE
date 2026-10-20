"""OllamaReplier against a local stand-in for the Ollama HTTP API."""

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from nexus_cove.agents.backends.ollama_replier import (
    MAX_REPLY_CHARS,
    ModelUnavailable,
    OllamaReplier,
    default_system_prompt,
)


def ollama_available() -> bool:
    """Check if Ollama daemon is reachable at the default URL."""
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


class _StubHandler(BaseHTTPRequestHandler):
    captured: dict = {}
    reply_content = "Bees dance to share where flowers are. What do you think they say?"

    def do_POST(self) -> None:  # noqa: N802 - http.server naming
        length = int(self.headers.get("Content-Length", "0"))
        _StubHandler.captured = json.loads(self.rfile.read(length).decode("utf-8"))
        body = json.dumps(
            {"message": {"role": "assistant", "content": self.reply_content}}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:  # keep test output quiet
        return


@pytest.fixture
def stub_server():
    server = HTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def test_reply_uses_chat_api_and_returns_content(stub_server: str) -> None:
    replier = OllamaReplier("llama3.2:3b", "SYSTEM TEXT", base_url=stub_server)
    text = replier.reply("Aegis-Worker says: hello")
    assert text.startswith("Bees dance")
    sent = _StubHandler.captured
    assert sent["model"] == "llama3.2:3b"
    assert sent["stream"] is False
    assert sent["messages"][0] == {"role": "system", "content": "SYSTEM TEXT"}
    assert sent["messages"][1] == {"role": "user", "content": "Aegis-Worker says: hello"}


def test_reply_is_truncated_to_limit(stub_server: str) -> None:
    _StubHandler.reply_content = "x" * (MAX_REPLY_CHARS + 500)
    try:
        text = OllamaReplier("m", "s", base_url=stub_server).reply("hi")
    finally:
        _StubHandler.reply_content = (
            "Bees dance to share where flowers are. What do you think they say?"
        )
    assert len(text) == MAX_REPLY_CHARS


def test_unreachable_model_raises_instead_of_inventing_text() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]
    replier = OllamaReplier("m", "s", base_url=f"http://127.0.0.1:{closed_port}", timeout=2)
    with pytest.raises(ModelUnavailable):
        replier.reply("hello")


def test_non_loopback_address_is_refused() -> None:
    with pytest.raises(ValueError):
        OllamaReplier("m", "s", base_url="http://192.168.1.10:11434")


def test_long_reply_is_trimmed_to_a_sentence_boundary() -> None:
    from nexus_cove.agents.backends.ollama_replier import MAX_REPLY_CHARS, _fit

    sentence = "Arches carry load to their supports. "
    text = sentence * ((MAX_REPLY_CHARS // len(sentence)) + 5)
    trimmed = _fit(text)
    assert len(trimmed) <= MAX_REPLY_CHARS
    assert trimmed.endswith(".")
    assert not trimmed.endswith(" ")


def test_short_reply_is_untouched() -> None:
    from nexus_cove.agents.backends.ollama_replier import _fit

    assert _fit("A complete short reply.") == "A complete short reply."


@pytest.mark.skipif(not ollama_available(), reason="Ollama not installed")
def test_ollama_replier_termux_integration() -> None:
    """Termux-compatible integration test with real Ollama daemon.

    Uses qwen2.5:0.5b model (~400 MB) which fits in constrained RAM environments.
    """
    model = "qwen2.5:0.5b"
    replier = OllamaReplier(model, default_system_prompt("TestAgent"))
    reply = replier.reply("TestAgent says: hello from Termux")

    # Basic sanity checks on the reply
    assert isinstance(reply, str)
    assert len(reply) > 0
    assert len(reply) <= MAX_REPLY_CHARS
    # Should be a coherent response, not an error message
    assert "error" not in reply.lower()
    assert "fail" not in reply.lower()

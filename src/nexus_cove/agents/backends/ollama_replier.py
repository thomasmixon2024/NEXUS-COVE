"""Chat replies from a local model through the Ollama HTTP API.

Only loopback addresses are accepted, so model traffic never leaves the
machine. Failures raise ``ModelUnavailable``; nothing is substituted
silently.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

DEFAULT_BASE_URL = "http://127.0.0.1:11434"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
MAX_REPLY_CHARS = 1200
MAX_REPLY_TOKENS = 320


def _fit(text: str, limit: int = MAX_REPLY_CHARS) -> str:
    """Shorten a reply to the limit, ending at a sentence boundary when one exists."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    if end > limit // 2:
        return cut[: end + 1]
    return cut.rstrip()


class ModelUnavailable(RuntimeError):
    """The local model could not produce a reply."""


class OllamaReplier:
    def __init__(
        self,
        model: str,
        system_prompt: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 120.0,
    ) -> None:
        host = urlsplit(base_url).hostname
        if host not in LOOPBACK_HOSTS:
            raise ValueError(f"base_url must use a loopback address, got {host!r}")
        self.model = model
        self.system_prompt = system_prompt
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        # Bypass any proxy settings: the model is local and must not be routed out.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def reply(self, user_text: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_text},
            ],
            "options": {"num_predict": MAX_REPLY_TOKENS},
        }
        request = urllib.request.Request(
            self.base_url + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError) as exc:
            raise ModelUnavailable(f"cannot reach {self.base_url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ModelUnavailable("model returned invalid JSON") from exc

        content = str((body.get("message") or {}).get("content", "")).strip()
        if not content:
            raise ModelUnavailable("model returned an empty reply")
        return _fit(content)

    async def areply(self, user_text: str) -> str:
        return await asyncio.to_thread(self.reply, user_text)


def default_system_prompt(agent_id: str) -> str:
    # Placeholder until per-agent personality files exist.
    return (
        f"You are {agent_id}, a young AI agent in the NEXUS COVE environment. "
        "Reply in two or three short sentences. Ask one curious question about what was said."
    )

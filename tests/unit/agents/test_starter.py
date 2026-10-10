import asyncio

import pytest

from nexus_cove.agents.backends.ollama_replier import ModelUnavailable
from nexus_cove.agents.personality import Personality
from nexus_cove.agents.starter import ConversationStarter


def _personality() -> Personality:
    return Personality(
        name="Aegis-Worker",
        temperament="Careful.",
        style="Calm.",
        mentor="Thomas",
        interests=("tunnels", "trust"),
        opening_questions=("Opener one?", "Opener two?"),
    )


class _Recorder:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def __call__(self, text: str) -> None:
        self.sent.append(text)


class _FakeReplier:
    def __init__(self, reply: str | None = None, fail: bool = False) -> None:
        self.reply_text = reply
        self.fail = fail
        self.prompts: list[str] = []

    async def areply(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.fail:
            raise ModelUnavailable("down")
        assert self.reply_text is not None
        return self.reply_text


def test_paused_sends_nothing() -> None:
    starter = ConversationStarter("Vigil-Worker", _personality(), paused=lambda: True)
    recorder = _Recorder()
    assert asyncio.run(starter.fire_once(recorder)) is None
    assert recorder.sent == []


def test_model_question_is_sent_and_mentions_the_interest() -> None:
    replier = _FakeReplier(reply="How do tunnels stay dry?")
    starter = ConversationStarter(
        "Vigil-Worker", _personality(), replier=replier, paused=lambda: False
    )
    recorder = _Recorder()
    text = asyncio.run(starter.fire_once(recorder))
    assert text == "How do tunnels stay dry?"
    assert recorder.sent == ["How do tunnels stay dry?"]
    assert "tunnels" in replier.prompts[0]
    assert "Vigil-Worker" in replier.prompts[0]


def test_falls_back_to_opening_question_when_model_is_down() -> None:
    starter = ConversationStarter(
        "Vigil-Worker", _personality(), replier=_FakeReplier(fail=True), paused=lambda: False
    )
    recorder = _Recorder()
    assert asyncio.run(starter.fire_once(recorder)) == "Opener one?"


def test_interests_rotate_across_fires() -> None:
    replier = _FakeReplier(reply="q")
    starter = ConversationStarter(
        "Vigil-Worker", _personality(), replier=replier, paused=lambda: False
    )
    recorder = _Recorder()

    async def three_fires() -> None:
        for _ in range(3):
            await starter.fire_once(recorder)

    asyncio.run(three_fires())
    assert "tunnels" in replier.prompts[0]
    assert "trust" in replier.prompts[1]
    assert "tunnels" in replier.prompts[2]


@pytest.mark.parametrize("bad", [0, -5])
def test_interval_must_be_positive(bad: float) -> None:
    with pytest.raises(ValueError):
        ConversationStarter("Vigil-Worker", _personality(), interval=bad)

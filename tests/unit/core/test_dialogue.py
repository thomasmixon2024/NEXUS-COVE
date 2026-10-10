import pytest

from nexus_cove.core.dialogue import DEFAULT_MAX_AGENT_TURNS, DialogueGuard


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_guard(
    max_agent_turns: int = 3, reopen_after: float = 300.0
) -> tuple[DialogueGuard, FakeClock]:
    clock = FakeClock()
    return DialogueGuard(
        max_agent_turns=max_agent_turns, reopen_after=reopen_after, clock=clock
    ), clock


def test_human_message_is_always_answered() -> None:
    guard, _ = make_guard(max_agent_turns=2)
    for _ in range(50):
        assert guard.should_reply("Thomas", "html_client") is True


def test_agent_replies_are_capped_per_counterpart() -> None:
    guard, _ = make_guard(max_agent_turns=3)
    results = [guard.should_reply("Vigil-Worker", "agent") for _ in range(5)]
    assert results == [True, True, True, False, False]
    assert guard.turns_used("Vigil-Worker") == 3


def test_cap_is_independent_for_each_counterpart() -> None:
    guard, _ = make_guard(max_agent_turns=1)
    assert guard.should_reply("Vigil-Worker", "agent") is True
    assert guard.should_reply("Vigil-Worker", "agent") is False
    assert guard.should_reply("Nexus-Manager", "manager") is True


def test_window_reopens_after_reopen_interval() -> None:
    guard, clock = make_guard(max_agent_turns=2, reopen_after=300.0)
    assert guard.should_reply("Vigil-Worker", "agent") is True
    assert guard.should_reply("Vigil-Worker", "agent") is True
    assert guard.should_reply("Vigil-Worker", "agent") is False
    clock.advance(299.0)
    assert guard.should_reply("Vigil-Worker", "agent") is False
    clock.advance(1.0)
    assert guard.should_reply("Vigil-Worker", "agent") is True
    assert guard.turns_used("Vigil-Worker") == 1


def test_each_window_allows_the_full_allowance_again() -> None:
    guard, clock = make_guard(max_agent_turns=10, reopen_after=300.0)
    for window in range(3):
        replies = [guard.should_reply("Aegis-Worker", "agent") for _ in range(12)]
        assert replies.count(True) == 10, f"window {window}"
        clock.advance(300.0)


def test_human_message_reopens_immediately() -> None:
    guard, clock = make_guard(max_agent_turns=1, reopen_after=300.0)
    assert guard.should_reply("Vigil-Worker", "agent") is True
    assert guard.should_reply("Vigil-Worker", "agent") is False
    assert guard.should_reply("Thomas", "html_client") is True
    assert guard.should_reply("Vigil-Worker", "agent") is True


def test_unknown_sender_kind_is_refused() -> None:
    guard, _ = make_guard()
    assert guard.should_reply("mystery", "unknown") is False
    assert guard.should_reply("mystery", "") is False


def test_defaults_are_ten_replies_per_five_minutes() -> None:
    guard = DialogueGuard()
    assert guard.max_agent_turns == DEFAULT_MAX_AGENT_TURNS == 10
    assert guard.reopen_after == 300.0


@pytest.mark.parametrize("bad_turns", [0, -1])
def test_limit_must_be_positive(bad_turns: int) -> None:
    with pytest.raises(ValueError):
        DialogueGuard(max_agent_turns=bad_turns)


def test_reopen_interval_must_not_be_negative() -> None:
    with pytest.raises(ValueError):
        DialogueGuard(reopen_after=-1.0)

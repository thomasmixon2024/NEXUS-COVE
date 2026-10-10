from pathlib import Path

import pytest

from nexus_cove.agents.personality import (
    build_system_prompt,
    bundled_personality,
    load_personality,
)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "agent.toml"
    path.write_text(body, encoding="utf-8")
    return path


GOOD = """
name = "Test-Agent"
mentor = "Thomas"
temperament = "Quiet."
style = "Short."
interests = ["stars"]
opening_questions = ["Why do stars shine?"]
"""


def test_bundled_personalities_load() -> None:
    for name in ("Aegis-Worker", "Vigil-Worker"):
        path = bundled_personality(name)
        assert path is not None, name
        personality = load_personality(path)
        assert personality.name == name
        assert personality.mentor == "Thomas"
        assert len(personality.interests) >= 1
        assert len(personality.opening_questions) >= 1


def test_unknown_agent_has_no_bundled_personality() -> None:
    assert bundled_personality("Nobody-Here") is None


def test_valid_file_loads(tmp_path: Path) -> None:
    personality = load_personality(_write(tmp_path, GOOD))
    assert personality.name == "Test-Agent"
    assert personality.interests == ("stars",)


@pytest.mark.parametrize(
    "body",
    [
        GOOD.replace('name = "Test-Agent"\n', ""),
        GOOD.replace('mentor = "Thomas"', 'mentor = "   "'),
        GOOD.replace('interests = ["stars"]', "interests = []"),
        GOOD.replace(
            'opening_questions = ["Why do stars shine?"]', 'opening_questions = "not a list"'
        ),
    ],
)
def test_invalid_file_is_rejected(tmp_path: Path, body: str) -> None:
    with pytest.raises(ValueError):
        load_personality(_write(tmp_path, body))


def test_system_prompt_carries_identity_mentor_and_interests(tmp_path: Path) -> None:
    prompt = build_system_prompt(load_personality(_write(tmp_path, GOOD)))
    assert "Test-Agent" in prompt
    assert "Thomas" in prompt
    assert "stars" in prompt

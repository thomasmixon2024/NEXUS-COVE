from pathlib import Path

import pytest

from nexus_cove.agents import pause


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv(pause.DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def test_agent_pause_is_independent_per_agent(data_dir: Path) -> None:
    pause.set_agent_paused("Aegis-Worker", True)
    assert pause.is_agent_paused("Aegis-Worker") is True
    assert pause.is_agent_paused("Vigil-Worker") is False


def test_resume_removes_the_flag(data_dir: Path) -> None:
    pause.set_agent_paused("Aegis-Worker", True)
    pause.set_agent_paused("Aegis-Worker", False)
    assert pause.is_agent_paused("Aegis-Worker") is False
    assert not (data_dir / "paused" / "Aegis-Worker.flag").exists()


def test_resume_when_not_paused_is_harmless(data_dir: Path) -> None:
    pause.set_agent_paused("Aegis-Worker", False)
    assert pause.is_agent_paused("Aegis-Worker") is False


def test_global_pause_silences_every_agent(data_dir: Path) -> None:
    (data_dir / pause.PAUSE_FILE_NAME).write_text("")
    assert pause.is_agent_paused("Aegis-Worker") is True
    assert pause.is_agent_paused("Vigil-Worker") is True


@pytest.mark.parametrize("bad", ["../escape", "a/b", "", "name with space", "x" * 65])
def test_unsafe_agent_names_are_rejected(data_dir: Path, bad: str) -> None:
    with pytest.raises(ValueError):
        pause.set_agent_paused(bad, True)

from pathlib import Path

import pytest

from nexus_cove.agents import pause


def test_not_paused_when_file_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(pause.DATA_DIR_ENV, str(tmp_path))
    assert pause.is_paused() is False


def test_paused_while_file_exists_and_resumes_when_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(pause.DATA_DIR_ENV, str(tmp_path))
    flag = tmp_path / pause.PAUSE_FILE_NAME
    flag.write_text("")
    assert pause.is_paused() is True
    flag.unlink()
    assert pause.is_paused() is False


def test_default_location_is_data_dir_relative_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(pause.DATA_DIR_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    assert pause.pause_file() == Path("data") / "PAUSE"

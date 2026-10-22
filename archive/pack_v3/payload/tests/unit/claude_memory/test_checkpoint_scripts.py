"""Tests for .claude/initialize_session.py and .claude/memory/save_checkpoint.py.

Each test copies the scripts into a throwaway git repo and runs them as
subprocesses, the way the hooks do.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_DIR = REPO_ROOT / ".claude"


def run(cwd: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        input=stdin,
        timeout=30,
    )


def git(cwd: Path, *args: str) -> str:
    return run(
        cwd,
        "git",
        "-c",
        "user.email=t@example.com",
        "-c",
        "user.name=t",
        *args,
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    (tmp_path / ".claude" / "memory").mkdir(parents=True)
    shutil.copy(CLAUDE_DIR / "initialize_session.py", tmp_path / ".claude")
    shutil.copy(CLAUDE_DIR / "memory" / "save_checkpoint.py", tmp_path / ".claude" / "memory")
    git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("one", encoding="utf-8")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "first")
    return tmp_path


def save(repo: Path, **fields) -> subprocess.CompletedProcess:
    payload = {
        "task_description": "Did a thing",
        "accomplishments": ["a"],
        "next_steps": ["b"],
        **fields,
    }
    (repo / "cp.json").write_text(json.dumps(payload), encoding="utf-8")
    return run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--file", "cp.json")


def load(repo: Path) -> str:
    return run(repo, sys.executable, ".claude/initialize_session.py").stdout


def current(repo: Path) -> dict:
    return json.loads((repo / ".claude/memory/current_checkpoint.json").read_text(encoding="utf-8"))


def test_manual_checkpoint_records_head_and_loader_says_matches(repo: Path) -> None:
    assert save(repo).returncode == 0
    assert current(repo)["git"]["head"] == git(repo, "rev-parse", "HEAD")
    out = load(repo)
    assert "Task: Did a thing" in out and "Checkpoint vs repo: MATCHES" in out


def test_loader_reports_new_commits_since_checkpoint(repo: Path) -> None:
    save(repo)
    (repo / "b.txt").write_text("two", encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "second")
    assert "Checkpoint vs repo: CHANGED - 1 new commit(s)" in load(repo)


def test_loader_handles_checkpoint_without_git_info(repo: Path) -> None:
    old = {"timestamp": "2000-01-01T00:00:00+00:00", "checkpoint_id": "cp_old",
           "task_description": "Old", "accomplishments": [], "next_steps": []}
    (repo / ".claude/memory/current_checkpoint.json").write_text(json.dumps(old), encoding="utf-8")
    out = load(repo)
    assert "UNKNOWN" in out and "newer than it" in out


def test_loader_with_no_data_or_corrupt_data_does_not_fail(repo: Path) -> None:
    assert "Starting fresh" in load(repo)
    (repo / ".claude/memory/current_checkpoint.json").write_text("{broken", encoding="utf-8")
    (repo / ".claude/memory/session_checkpoints.jsonl").write_text(
        'not json\n{"task_description": "From journal", "accomplishments": [], "next_steps": []}\n',
        encoding="utf-8")
    assert "From journal" in load(repo)


def test_auto_checkpoint_carries_the_manual_task_and_notes_uncommitted_files(repo: Path) -> None:
    save(repo)
    (repo / "a.txt").write_text("changed", encoding="utf-8")
    result = run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--auto",
                 stdin='{"session_id": "abc"}')
    assert result.returncode == 0
    cp = current(repo)
    assert cp["source"] == "auto" and cp["session_id"] == "abc"
    assert cp["task_description"] == "Did a thing" and cp["next_steps"] == ["b"]
    # Names must be intact (the first character was once cut off), and the
    # checkpoint's own files under .claude/memory must not be listed.
    assert cp["metadata"]["files_modified"] == ["a.txt", "cp.json"]
    assert cp["carried_from"]["source"] == "manual"
    assert "Task below comes from" in load(repo)


def test_auto_checkpoint_is_skipped_when_nothing_changed(repo: Path) -> None:
    save(repo)
    run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--auto", stdin="{}")
    lines_before = (repo / ".claude/memory/session_checkpoints.jsonl").read_text().splitlines()
    result = run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--auto", stdin="{}")
    assert "nothing saved" in result.stdout
    journal = repo / ".claude/memory/session_checkpoints.jsonl"
    assert journal.read_text().splitlines() == lines_before


def test_second_auto_keeps_pointing_at_the_original_manual_checkpoint(repo: Path) -> None:
    save(repo)
    manual_id = current(repo)["checkpoint_id"]
    run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--auto", stdin="{}")
    (repo / "c.txt").write_text("x", encoding="utf-8")
    run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--auto", stdin="{}")
    assert current(repo)["carried_from"]["checkpoint_id"] == manual_id


def test_auto_after_a_malformed_checkpoint_does_not_invent_an_origin(repo: Path) -> None:
    (repo / ".claude/memory/current_checkpoint.json").write_text('{"keep": "me"}', encoding="utf-8")
    run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--auto", stdin="{}")
    assert current(repo)["carried_from"] is None
    assert "comes from" not in load(repo)


@pytest.mark.parametrize(
    "bad",
    [{"task_description": 5}, {"task_description": " "}, {"accomplishments": "x"},
     {"accomplishments": [1]}, {"next_steps": "x"}, {"metadata": []}],
)
def test_manual_checkpoint_rejects_bad_fields(repo: Path, bad: dict) -> None:
    result = save(repo, **bad)
    assert result.returncode == 1 and "Checkpoint not saved" in result.stderr
    assert not (repo / ".claude/memory/current_checkpoint.json").exists()


def test_manual_checkpoint_rejects_non_object_and_missing_file(repo: Path) -> None:
    (repo / "cp.json").write_text("[1]", encoding="utf-8")
    result = run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--file", "cp.json")
    assert result.returncode == 1
    result = run(repo, sys.executable, ".claude/memory/save_checkpoint.py", "--file", "nope.json")
    assert result.returncode == 1

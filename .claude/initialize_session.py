#!/usr/bin/env python3
"""Session continuity loader for NEXUS COVE.

Prints the latest real checkpoint (written by save_checkpoint.py), says whether
the repo has changed since it was written, and shows the current git state.
Run by the SessionStart hook, whose output Claude Code adds to the model's
context, so it stays short. Never fails the session: missing or broken data
prints a notice and exits 0.
"""
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEM = ROOT / ".claude" / "memory"
CURRENT = MEM / "current_checkpoint.json"
JOURNAL = MEM / "session_checkpoints.jsonl"
MAX_ITEMS = 8
MAX_ITEM_CHARS = 160


def load_checkpoint():
    try:
        data = json.loads(CURRENT.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass
    try:  # fall back to the newest journal line that parses
        for line in reversed(JOURNAL.read_text(encoding="utf-8").splitlines()):
            try:
                data = json.loads(line)
            except ValueError:
                continue
            if isinstance(data, dict):
                return data
    except OSError:
        pass
    return None


def parse_time(ts):
    try:
        then = datetime.fromisoformat(ts)
        return then if then.tzinfo else then.replace(tzinfo=UTC)
    except (TypeError, ValueError):
        return None


def age_text(ts):
    then = parse_time(ts)
    if then is None:
        return "unknown age"
    hours = (datetime.now(UTC) - then).total_seconds() / 3600
    return f"{hours:.1f} h ago" if hours < 48 else f"{hours / 24:.1f} days ago"


def git(*args):
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                           text=True, timeout=5)
        return r.stdout.rstrip("\n") if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def clip(item):
    item = str(item)
    return item if len(item) <= MAX_ITEM_CHARS else item[:MAX_ITEM_CHARS - 3] + "..."


def show_list(title, items):
    if not isinstance(items, list) or not items:
        return
    print(title)
    for item in items[:MAX_ITEMS]:
        print(f"   - {clip(item)}")
    if len(items) > MAX_ITEMS:
        print(f"   (+{len(items) - MAX_ITEMS} more in .claude/memory/session_checkpoints.jsonl)")


def compare_with_repo(cp):
    """One line saying whether the checkpoint still matches the repo."""
    current = git("rev-parse", "HEAD")
    if current is None:
        return "NO GIT - cannot compare with the repo"
    saved = (cp.get("git") or {}).get("head")
    if saved == current:
        return f"MATCHES - HEAD unchanged since the checkpoint ({current[:7]})"
    if saved:
        count = git("rev-list", "--count", f"{saved}..HEAD")
        if count is None:
            return (
                f"DIVERGED - checkpoint commit {saved[:7]} is not an ancestor of HEAD "
                f"({current[:7]}); branch switched or history rewritten"
            )
        return (
            f"CHANGED - {count} new commit(s) since the checkpoint "
            f"({saved[:7]} -> {current[:7]})"
        )
    # Older checkpoint without git facts: compare commit time with checkpoint time.
    committed = parse_time(git("log", "-1", "--format=%cI") or "")
    written = parse_time(cp.get("timestamp", ""))
    if committed and written:
        if committed > written:
            return (
                "UNKNOWN - checkpoint has no git info; "
                "the latest commit is newer than it, so the repo has changed"
            )
        return (
            "UNKNOWN - checkpoint has no git info; "
            "the latest commit is older than it, so the repo likely matches"
        )
    return "UNKNOWN - checkpoint has no git info"


def main():
    print("SESSION CONTINUITY GUIDE")
    print("=" * 60)
    cp = load_checkpoint()
    if not cp:
        print("No previous checkpoint found. Starting fresh.")
    else:
        origin = cp.get("carried_from") if cp.get("source") == "auto" else None
        if not (isinstance(origin, dict) and origin.get("checkpoint_id")):
            origin = None
        print(
            f"Last checkpoint: {cp.get('checkpoint_id', 'unknown')} "
            f"[{cp.get('source', 'manual')}] {cp.get('timestamp', 'unknown')} "
            f"({age_text(cp.get('timestamp'))})"
        )
        if origin:
            print(f"Task below comes from {origin['checkpoint_id']} checkpoint "
                  f"({age_text(origin.get('timestamp'))})")
        print(f"Task: {cp.get('task_description', 'not recorded')}")
        show_list("Accomplishments:", cp.get("accomplishments"))
        show_list("Next steps:", cp.get("next_steps"))
        show_list("Files touched:", (cp.get("metadata") or {}).get("files_modified"))
        print("-" * 60)
        print(f"Checkpoint vs repo: {compare_with_repo(cp)}")

    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    if branch:
        # Same rule as save_checkpoint.py: the checkpoint files are bookkeeping, not work.
        dirty = [line for line in (git("status", "--porcelain") or "").splitlines()
                 if not line[3:].startswith(".claude/memory/")]
        print(f"Git now: branch {branch}, {len(dirty)} uncommitted change(s)")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never block the session on a loader bug
        print(f"Session loader error (continuing anyway): {exc}")

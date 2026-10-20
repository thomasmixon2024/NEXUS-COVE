#!/usr/bin/env python3
"""Write a session checkpoint.

  --auto           SessionEnd hook. Records git facts and carries forward the
                   last manual task and next steps. Skipped when the git state
                   is identical to the previous automatic record.
  --file FILE.json Manual checkpoint. FILE must contain task_description (str)
                   and accomplishments (list of str); next_steps (list of str)
                   and metadata (object) are optional.

Every checkpoint records the git HEAD it was written at, so the loader can tell
whether the repo has changed since. Appends to session_checkpoints.jsonl and
replaces current_checkpoint.json (atomically).
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEM = ROOT / ".claude" / "memory"
CURRENT = MEM / "current_checkpoint.json"
JOURNAL = MEM / "session_checkpoints.jsonl"
GIT_TIMEOUT = 3  # seconds; the SessionEnd hook has a small time budget
MAX_CHANGED_FILES = 50


def git(*args):
    """Run git in the repo root. Returns stdout without the trailing newline, or None."""
    try:
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                           text=True, timeout=GIT_TIMEOUT)
        return r.stdout.rstrip("\n") if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def git_state():
    """Facts about the repo right now. Fields are None/empty when git is unavailable."""
    state = {"head": None, "last_commit": None, "branch": None, "changed": []}
    log = git("log", "-1", "--format=%H%n%h %s")
    if log:
        head, _, subject = log.partition("\n")
        state["head"], state["last_commit"] = head, subject
    status = git("status", "--porcelain=v1", "--branch")
    if status:
        lines = status.splitlines()
        if lines and lines[0].startswith("## "):
            state["branch"] = lines[0][3:].split("...")[0]
            lines = lines[1:]
        # The checkpoint files themselves change every session; they are not work.
        state["changed"] = [p for p in (line[3:] for line in lines)
                            if not p.startswith(".claude/memory/")]
    return state


def last_checkpoint():
    try:
        data = json.loads(CURRENT.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def stdin_session_id():
    """SessionEnd hooks send JSON on stdin that includes session_id."""
    if sys.stdin.isatty():
        return None
    try:
        data = json.loads(sys.stdin.read() or "{}")
        return data.get("session_id") if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def public_git(state):
    """The git facts stored in a checkpoint (file names go in metadata, not here)."""
    return {"head": state["head"], "branch": state["branch"],
            "last_commit": state["last_commit"], "uncommitted": len(state["changed"])}


def build_auto(session_id, state, prev):
    """Carry the last manual task forward and add git facts. Returns None to skip."""
    git_facts = public_git(state)
    files = state["changed"][:MAX_CHANGED_FILES]
    if (prev.get("source") == "auto" and prev.get("git") == git_facts
            and (prev.get("metadata") or {}).get("files_modified") == files):
        return None
    if prev.get("source") == "auto":
        origin = prev.get("carried_from")
    elif prev.get("checkpoint_id"):
        origin = {"checkpoint_id": prev.get("checkpoint_id"),
                  "timestamp": prev.get("timestamp"), "source": prev.get("source", "manual")}
    else:
        origin = None
    return {
        "task_description": prev.get("task_description", "Session ended (no manual summary)"),
        "accomplishments": [f"Auto record at session end. Last commit: {state['last_commit'] or 'none'}",
                            f"{len(state['changed'])} uncommitted change(s) at session end"],
        "next_steps": prev.get("next_steps", []),
        "metadata": {"files_modified": files},
        "source": "auto",
        "carried_from": origin,
        "git": git_facts,
        "session_id": session_id,
    }


def string_list(data, key, required):
    value = data.get(key) if required else data.setdefault(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"{key} must be a list of strings")


def build_manual(path, session_id, state):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("checkpoint file must contain a JSON object")
    if not isinstance(data.get("task_description"), str) or not data["task_description"].strip():
        raise ValueError("task_description must be a non-empty string")
    string_list(data, "accomplishments", required=True)
    string_list(data, "next_steps", required=False)
    if not isinstance(data.setdefault("metadata", {}), dict):
        raise ValueError("metadata must be an object")
    data.pop("carried_from", None)  # set only by --auto
    data["source"] = "manual"
    data["git"] = public_git(state)
    data["session_id"] = session_id
    return data


def write_checkpoint(data):
    MEM.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")
    fd, tmp = tempfile.mkstemp(dir=MEM, prefix=".current.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, CURRENT)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--auto", action="store_true")
    mode.add_argument("--file")
    args = ap.parse_args()

    # Only the SessionEnd hook (--auto) sends JSON on stdin; manual runs must not block on it.
    session_id = (stdin_session_id() if args.auto else None) or os.getenv("CLAUDE_SESSION_ID", "unknown")
    state = git_state()
    try:
        data = (build_auto(session_id, state, last_checkpoint() or {}) if args.auto
                else build_manual(args.file, session_id, state))
        if data is None:
            print("No change since the last automatic checkpoint; nothing saved")
            return 0
        now = datetime.now(timezone.utc)
        data["timestamp"] = now.isoformat()
        data["checkpoint_id"] = f"cp_{now:%Y%m%d_%H%M%S}"
        write_checkpoint(data)
    except (OSError, ValueError) as exc:
        print(f"Checkpoint not saved: {exc}", file=sys.stderr)
        return 1
    print(f"Saved {data['checkpoint_id']} ({data['source']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

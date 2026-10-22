# NEXUS COVE memory network, patch v3 (NOT INSTALLED)

Nothing here has been applied to `~/NEXUS-COVE`. `install.py` is a dry run unless you pass `--apply`.

## Install (Termux Ubuntu)

```bash
unzip nexuscove_memory_network_v3.zip -d ~/pack_v3
python3 ~/pack_v3/install.py --repo ~/NEXUS-COVE            # dry run, prints the plan
python3 ~/pack_v3/install.py --repo ~/NEXUS-COVE --apply    # after you approve the plan
cd ~/NEXUS-COVE && python -m pytest -q                       # runs the real suite
```

What the installer will not do: delete anything, touch `current_checkpoint.json` or `session_checkpoints.jsonl`, or replace `CLAUDE.md` / `settings.json` wholesale. Replaced files are copied to `.claude/backups/memory-network-<time>/` first. To undo, copy them back.

## What changed from v2, and why

Bugs fixed
- `memory.py`: every `append` re-read the whole log, and after message 100 it wrote a new snapshot file on *every* message. Now the count is tracked in memory and a snapshot is written every 100th message.
- `memory.py`: the worker builds `AgentMemory(path)` with no name, so every agent was called "unknown" and they all shared one highlights file and one session file. The name now defaults to the log file name, and all sidecar files are per agent.
- `memory.py`: highlight keywords matched inside words ("prefix" counted as "fix"). They now match at word starts. Redundant dead code and a no-op loader were removed.
- `memory.py`: `except Exception: pass` hid failures, against CLAUDE.md policy. Only OS errors in the optional extras are caught, and they are logged. Agent names are sanitized for file names. Writes are atomic.
- `save_checkpoint.py`: `git status` output was stripped before parsing, which cut the first character off the first file name. Fixed, and the checkpoint's own files no longer count as uncommitted work.
- `checkpoint_system.py`: defaulted to the current directory instead of its own, so running it elsewhere created stray `.claude/memory` folders.
- `MEMORY_ENHANCEMENTS.md` described features that do not exist (rotation, `get_memory_stats`, scoring, tuning options). Rewritten to match the code. `CHECKPOINT_AGENT_INVOCATIONS.md` had stray LaTeX; fixed.

Improvements
- Every checkpoint records the git HEAD it was written at. The loader prints `Checkpoint vs repo:` as MATCHES, CHANGED (n new commits), DIVERGED or UNKNOWN. That answers "has the repo changed since the last checkpoint?" directly.
- The loader shows the age of the manual checkpoint an automatic record carried its task from, so an old task is not mistaken for a recent one.
- Automatic records are skipped when nothing changed since the last one. Manual checkpoints are validated (types, non-empty task).
- Hooks use `${CLAUDE_PROJECT_DIR:-.}` (no hard-coded path) and `"timeout": 10`. Claude Code gives SessionEnd hooks only 1.5 s unless the hook sets a timeout, so v2's auto checkpoint could have been cut off.
- `CLAUDE.md` no longer tells the model to `cat CLAUDE.md` (it is already loaded). It adds the bash equivalents of the PowerShell commands.

## Verified, and what is not

- 37 new tests pass (15 for the `.claude` scripts, 22 for `memory.py` behavior), run against a stand-in for `nexus_cove.utils.jsonl` because that module was not in the zip. Run the suite in the real repo to confirm.
- Installer tried on a copy of a repo shaped like yours: dry run changes nothing, apply is idempotent, history and unrelated settings kept.
- Per the Claude Code hooks docs, SessionStart hook output is added to the model's context (this closes v2's open item 2), and the hook also fires on resume, clear and compact.
- Not checked: your real `settings.json`, the existing tests that import `nexus_cove.agents.tools`, and anything outside the zip.

## Decisions left for you

1. The original goal was "clear the cache periodically, keep highlights". `memory.py` still never rotates the message log. Implementing rotation touches how the worker reads history, so I left it out. Say so if you want it.
2. Checkpoint logic exists in four places (`memory.py`, `checkpoint_system.py`, `save_checkpoint.py`, the loader). I kept `checkpoint_system.py` as a compatible shim because I cannot see what imports it. Once you grep the repo, it can likely go.
3. `.claude/memory/SESSION_COMPLETE_SUMMARY.md` says "COMPLETED" and "verified functional" for skills; per the Definition of Done that wording needs evidence or removal. Left unchanged as history.
4. The installer reports, but does not remove, the old end-of-file session section in `CLAUDE.md`.

After installing, `CHECKPOINT_AFTER_INSTALL.json` is a ready summary you can save with
`python3 .claude/memory/save_checkpoint.py --file CHECKPOINT_AFTER_INSTALL.json`.

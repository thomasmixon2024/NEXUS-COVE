# Agent memory (`src/nexus_cove/agents/memory.py`)

This page describes what `AgentMemory` does today. An earlier version of this file described features that were never implemented (rotating message files, `get_memory_stats`, `create_checkpoint(name)`, `list_checkpoints`, weighted highlight scoring, constructor tuning options). None of those exist.

## What it does

- **Message log.** `append(direction, peer, text)` writes one JSON line to the agent's `.jsonl` file. `entries()` and `recent(n)` read it back. The log is never edited, rotated or cleared.
- **Highlights.** Each appended message is scanned line by line. A line is kept if it is a bullet (`-`, `*`, `•`), a numbered item, a quote (`>`), or contains `key point`, `important`, `decision`, `error`, `success`, `todo`, `fix` or `critical` at the start of a word (`fixed` matches, `prefix` does not). The newest 50 are stored in `<agent>.highlights.json`. `get_highlights()` returns them.
- **Snapshots.** `save_checkpoint(description)` writes `checkpoints/<agent>_checkpoint_<time>.json` with the message count, highlights and last 10 entries. One is written automatically every `checkpoint_every` messages (default 100). `load_latest_checkpoint()` returns the newest one.
- **Start-up journal.** Creating an `AgentMemory` appends a line to `session/<agent>.sessions.jsonl` (capped at 50 lines) and updates `session/<agent>.current.json`. `get_latest_session_checkpoint()`, `get_session_checkpoint_history(limit)` and `print_session_continuity_guide()` read them. `startup_flush_with_highlight_retention()` returns the retained highlights and records one more journal line; it deletes nothing.

## Naming

If `agent_name` is not given it defaults to the log file's name without extension, so `Aegis-Worker.jsonl` gives agent `Aegis-Worker`. The worker passes only the path, so each worker gets its own highlights and journal files. Names are reduced to letters, digits, `.`, `_` and `-` before they are used in a file name.

## Behavior notes

- The message count is read from disk once per instance, then tracked in memory. `append` does not re-read the log.
- Highlights and snapshots are written atomically (temp file, then rename).
- If saving highlights or a snapshot fails with an OS error, the message is already stored; the error is logged and `append` returns normally.
- An unreadable sidecar file is logged and treated as empty.
- Not implemented: removing or archiving old messages, loading a named snapshot back into the log, per-agent tuning options. Add them here only when they exist in the code.

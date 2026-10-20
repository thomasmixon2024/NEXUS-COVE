## Session Start and End (required, every session)

**Start.** A SessionStart hook runs `python3 .claude/initialize_session.py`; its output appears in your context under "SESSION CONTINUITY GUIDE". If it is missing, run that command yourself. CLAUDE.md is already loaded, so do not `cat` it. Open your first reply with the last task, the first next step, and the "Checkpoint vs repo" line (MATCHES, CHANGED, DIVERGED or UNKNOWN). Ask only if the checkpoint conflicts with the user's request.

**End.** When a significant task finishes, save a manual checkpoint: write a JSON file outside the repo (for example `/tmp/checkpoint.json`) with `task_description` (string), `accomplishments` (list of strings) and `next_steps` (list of strings), then run `python3 .claude/memory/save_checkpoint.py --file /tmp/checkpoint.json`. A SessionEnd hook also records git facts automatically, but it cannot describe your work, so the manual checkpoint is required.

**Shell on Termux/Ubuntu** (the commands under "Development commands" are PowerShell):

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q && python -m compileall -q src tests
```

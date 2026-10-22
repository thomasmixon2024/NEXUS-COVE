#!/usr/bin/env bash
# apply-continuity-fix.sh
# Patches NEXUS-COVE CLAUDE.md and .claude/settings.json.
# Usage: bash apply-continuity-fix.sh [/path/to/NEXUS-COVE]
set -euo pipefail

REPO="${1:-$PWD}"
cd "$REPO"

[[ -f CLAUDE.md ]] || { echo "CLAUDE.md not found in $REPO" >&2; exit 1; }
mkdir -p .claude

STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR=".patch-backups/$STAMP"
mkdir -p "$BACKUP_DIR"
cp CLAUDE.md "$BACKUP_DIR/CLAUDE.md"
if [[ -f .claude/settings.json ]]; then
  cp .claude/settings.json "$BACKUP_DIR/settings.json"
fi
echo "Backups written to $BACKUP_DIR"

python3 - <<'PY'
import pathlib, re, sys

FENCE = "`" * 3
path = pathlib.Path("CLAUDE.md")
text = path.read_text(encoding="utf-8")

NEW_BLOCK = """<!-- BEGIN session-continuity (managed by install.py; edit the file in the patch, not here) -->
## Session Start and End (required, every session)

**Start.** A SessionStart hook runs `python3 .claude/initialize_session.py` (use `python` on Windows). Its output appears in your context under "SESSION CONTINUITY GUIDE". If that output is missing, run the command yourself once. CLAUDE.md is already loaded, so do not read it again. Open your first reply with the last task, the first next step, and the "Checkpoint vs repo" line (MATCHES, CHANGED, DIVERGED or UNKNOWN). Ask only if the checkpoint conflicts with the user's request.

**End.** When a significant task finishes, save a manual checkpoint. Write a JSON file to the OS temp directory containing `task_description` (string), `accomplishments` (list of strings) and `next_steps` (list of strings). Then run `python3 .claude/memory/save_checkpoint.py --file <that path>` (use `python` on Windows). The SessionEnd hook records git facts automatically but cannot describe your work, so the manual checkpoint is required.

**Shell setup.** The commands under "Development commands" are PowerShell syntax. Use the block for your environment.

Windows (PowerShell, repo root):

@@FENCE@@powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q; if ($LASTEXITCODE -ne 0) { throw "tests failed" }
python -m compileall -q src tests
@@FENCE@@

Termux/Ubuntu (bash, repo root):

@@FENCE@@bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q && python -m compileall -q src tests
@@FENCE@@
<!-- END session-continuity -->""".replace("@@FENCE@@", FENCE)

begin = text.index("<!-- BEGIN session-continuity")
end_marker = "<!-- END session-continuity -->"
end = text.index(end_marker) + len(end_marker)
text = text[:begin] + NEW_BLOCK + text[end:]

old_continuity = re.compile(
    r"To begin the next session focused on agent memory, simply run:\s+"
    r"python \.claude/initialize_session\.py\s+"
    r"This will load your session continuity guide showing exactly where we left off and what to work on next\.",
)
text, n = old_continuity.subn(
    "The SessionStart hook loads the continuity guide automatically, showing where the last session "
    "left off and what to work on next. Run `python3 .claude/initialize_session.py` manually only if "
    "the hook output is missing.",
    text,
)
if n != 1:
    sys.exit("ERROR: bottom Session Continuity paragraph not found exactly once")

text, n = re.subn(
    r"8\.\s+Ruff passes when installed\.",
    "8. `python -m ruff check .` passes. If Ruff is not installed, report the check as NOT RUN, not as passed.",
    text,
)
if n != 1:
    sys.exit("ERROR: Ruff Definition-of-Done line not found exactly once")

fence_lines = sum(1 for line in text.splitlines() if line.lstrip().startswith(FENCE))
if fence_lines % 2 != 0:
    sys.exit(f"ERROR: unbalanced code fences ({fence_lines})")

path.write_text(text, encoding="utf-8")
print(f"CLAUDE.md patched; fences balanced ({fence_lines})")
PY

cat > .claude/settings.json <<'JSON'
{
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true
  },
  "permissions": {
    "allow": [
      "Bash(python3 .claude/initialize_session.py)",
      "Bash(python .claude/initialize_session.py)",
      "Bash(python3 .claude/memory/save_checkpoint.py *)",
      "Bash(python .claude/memory/save_checkpoint.py *)"
    ]
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR:-.}/.claude/initialize_session.py\" || python \"${CLAUDE_PROJECT_DIR:-.}/.claude/initialize_session.py\"",
            "timeout": 30
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CLAUDE_PROJECT_DIR:-.}/.claude/memory/save_checkpoint.py\" --auto || python \"${CLAUDE_PROJECT_DIR:-.}/.claude/memory/save_checkpoint.py\" --auto",
            "timeout": 30
          }
        ]
      }
    ]
  }
}
JSON

python3 -m json.tool .claude/settings.json > /dev/null
echo "settings.json written and validated"
echo "Review with: git diff -- CLAUDE.md .claude/settings.json"
echo "Restore if needed: cp $BACKUP_DIR/CLAUDE.md CLAUDE.md"

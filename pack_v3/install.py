#!/usr/bin/env python3
"""Install the NEXUS COVE memory-network patch into a repo.

  python3 install.py --repo ~/NEXUS-COVE            dry run: shows what would change
  python3 install.py --repo ~/NEXUS-COVE --apply    make the changes

Safety rules:
- Dry run is the default; nothing is written without --apply.
- Nothing is ever deleted. Any file that gets replaced is first copied to
  <repo>/.claude/backups/memory-network-<time>/.
- Checkpoint history (.claude/memory/current_checkpoint.json and
  session_checkpoints.jsonl) is never read, written or replaced.
- CLAUDE.md gets one managed block (between BEGIN/END markers); the rest of the
  file is left alone. Other session sections are reported, not removed.
- settings.json is merged, not replaced: other keys and hooks stay as they are.
"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAYLOAD = HERE / "payload"
BEGIN = "<!-- BEGIN session-continuity (managed by install.py; edit the file in the patch, not here) -->"
END = "<!-- END session-continuity -->"
# Files copied as they are (path relative to payload/ and to the repo).
FILES = [
    ".claude/initialize_session.py",
    ".claude/memory/save_checkpoint.py",
    ".claude/memory/checkpoint_system.py",
    "src/nexus_cove/agents/memory.py",
    "tests/unit/agents/test_memory_behavior.py",
    "tests/unit/claude_memory/test_checkpoint_scripts.py",
    "MEMORY_ENHANCEMENTS.md",
    "CHECKPOINT_AGENT_INVOCATIONS.md",
]
SESSION_HEADING = re.compile(r"^#{1,4}\s.*session.*(start|end|continuity|checkpoint)", re.I)


def line_delta(old, new):
    added = removed = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, old.splitlines(), new.splitlines(), autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            removed += i2 - i1
        if tag in ("replace", "insert"):
            added += j2 - j1
    return added, removed


class Installer:
    def __init__(self, repo, apply):
        self.repo = repo
        self.apply = apply
        self.backup_dir = repo / ".claude" / "backups" / f"memory-network-{datetime.now():%Y%m%d_%H%M%S}"
        self.changes = 0

    def say(self, tag, path, note=""):
        print(f"  [{tag:6}] {path}{'  ' + note if note else ''}")

    def backup(self, rel):
        target = self.repo / rel
        dest = self.backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, dest)

    def write(self, rel, text, existed):
        target = self.repo / rel
        if existed:
            self.backup(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def copy_file(self, rel):
        new = (PAYLOAD / rel).read_text(encoding="utf-8")
        target = self.repo / rel
        if not target.exists():
            self.say("new", rel)
            self.changes += 1
            if self.apply:
                self.write(rel, new, existed=False)
            return
        old = target.read_text(encoding="utf-8")
        if old == new:
            self.say("same", rel)
            return
        added, removed = line_delta(old, new)
        self.say("update", rel, f"(+{added} -{removed} lines, old copy goes to backups)")
        self.changes += 1
        if self.apply:
            self.write(rel, new, existed=True)

    def claude_md(self):
        rel = "CLAUDE.md"
        block = f"{BEGIN}\n{(PAYLOAD / 'CLAUDE_BLOCK.md').read_text(encoding='utf-8').strip()}\n{END}\n"
        target = self.repo / rel
        if not target.exists():
            self.say("new", rel, "(only the session block)")
            self.changes += 1
            if self.apply:
                self.write(rel, block, existed=False)
            return
        old = target.read_text(encoding="utf-8")
        pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.S)
        outside = old
        if pattern.search(old):
            new = pattern.sub(lambda _m: block, old, count=1)
            outside = pattern.sub("", old)
        else:
            lines = old.splitlines(keepends=True)
            first = next((i for i, l in enumerate(lines) if l.strip()), None)
            at = first + 1 if first is not None and lines[first].startswith("# ") else 0
            new = "".join(lines[:at]) + ("\n" if at else "") + block + "\n" + "".join(lines[at:])
        if new == old:
            self.say("same", rel)
        else:
            added, removed = line_delta(old, new)
            self.say("update", rel, f"(+{added} -{removed} lines, session block under the title)")
            self.changes += 1
            if self.apply:
                self.write(rel, new, existed=True)
        for number, line in enumerate(outside.splitlines(), 1):
            if SESSION_HEADING.match(line) or "initialize_session" in line:
                print(f"           NOTE: CLAUDE.md line {number} outside the block also covers sessions: "
                      f"{line.strip()[:90]!r}. Remove it by hand if it is the old end-of-file section.")

    def settings(self):
        rel = ".claude/settings.json"
        fragment = json.loads((PAYLOAD / ".claude/settings.hooks.json").read_text(encoding="utf-8"))
        target = self.repo / rel
        existed = target.exists()
        if existed:
            try:
                data = json.loads(target.read_text(encoding="utf-8"))
            except ValueError as exc:
                self.say("SKIP", rel, f"not valid JSON ({exc}); fix it, then run again")
                return
            if not isinstance(data, dict):
                self.say("SKIP", rel, "top level is not an object")
                return
        else:
            data = {}
        before = json.dumps(data, sort_keys=True)

        allow = data.setdefault("permissions", {}).setdefault("allow", [])
        for rule in fragment["permissions"]["allow"]:
            if rule not in allow:
                allow.append(rule)
        hooks = data.setdefault("hooks", {})
        for event, groups in fragment["hooks"].items():
            new_hook = groups[0]["hooks"][0]
            script = "save_checkpoint.py" if event == "SessionEnd" else "initialize_session.py"
            existing = hooks.setdefault(event, [])
            found = False
            for group in existing:
                for hook in group.get("hooks", []):
                    if script in hook.get("command", ""):
                        hook.update(new_hook)  # same script: bring command and timeout up to date
                        found = True
            if not found:
                existing.append({"hooks": [dict(new_hook)]})

        if json.dumps(data, sort_keys=True) == before:
            self.say("same", rel)
            return
        self.say("merge", rel, "(adds/updates the two hooks and two allow rules; other settings kept)")
        self.changes += 1
        if self.apply:
            self.write(rel, json.dumps(data, indent=2) + "\n", existed=existed)

    def run(self):
        mode = "APPLYING" if self.apply else "DRY RUN (nothing will be written)"
        print(f"{mode}: {self.repo}")
        for rel in FILES:
            self.copy_file(rel)
        self.claude_md()
        self.settings()
        print()
        if not self.changes:
            print("Already up to date.")
        elif self.apply:
            print(f"Done: {self.changes} change(s). Replaced files were backed up under {self.backup_dir}"
                  if self.backup_dir.exists() else f"Done: {self.changes} change(s). Nothing needed a backup.")
            print("Checking the loader:\n")
            subprocess.run([sys.executable, str(self.repo / ".claude/initialize_session.py")], cwd=self.repo)
        else:
            print(f"{self.changes} change(s) pending. Run again with --apply to install.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, type=Path, help="path to the NEXUS-COVE repo")
    ap.add_argument("--apply", action="store_true", help="write the changes (default is a dry run)")
    args = ap.parse_args()
    repo = args.repo.expanduser().resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 1
    if not (repo / ".git").exists():
        print("Warning: no .git folder here; the loader will report NO GIT.")
    Installer(repo, args.apply).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())

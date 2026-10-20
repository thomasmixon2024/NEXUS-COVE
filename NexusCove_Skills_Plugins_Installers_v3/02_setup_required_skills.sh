#!/usr/bin/env bash
# ============================================================
# Nexus Cove - REQUIRED skills
# Writes user-level SKILL.md files to ~/.claude/skills/ and
# verifies them. Built-in agent types are reported, not written.
# ============================================================
set -Eeuo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
init_log required_skills

info "general-purpose and Plan are built-in Claude Code agent types. They are not files and need no install. Verify with /agents inside Claude Code."

write_skill code-review <<'EOF'
---
name: code-review
description: Review Nexus Cove code changes for correctness, safety, and definition-of-done compliance. Use when reviewing a diff, a pull request, or changed files before merge.
---

# Nexus Cove code review

1. Identify the change set with `git status` and `git diff`. Review only changed code unless told otherwise.
2. Check correctness: edge cases, error handling, async and transport behavior, resource cleanup, and input validation.
3. Run the definition-of-done checks from the project root:
   - `python -m ruff check .`
   - `python -m compileall -q src tests`
   - `python -m pytest -q`
4. Report findings ordered by severity: blocking, should-fix, nit. Give each one a file:line reference and a concrete fix.
5. Do not approve if lint, compile, or tests fail. Tests are the authoritative evidence.
EOF

write_skill simplify <<'EOF'
---
name: simplify
description: Simplify recently changed Nexus Cove code for reuse, clarity, and efficiency without changing behavior. Use after a change works and its tests pass.
---

# Simplify

1. Scope the work to recently changed code unless the user names a wider scope.
2. Find duplicated logic and reuse existing helpers before adding new ones.
3. Remove dead code, unused imports, and needless indirection.
4. Keep the layer boundaries intact: transport, orchestration, storage, and observability. Do not move logic across layers just to shorten a file.
5. Preserve behavior. Run ruff, compileall, and pytest after each change, and revert any change that breaks them.
EOF

for skill in code-review simplify; do
    if skill_present "$skill"; then
        success "Verified skill present: ${skill}"
    else
        finish_failure "Skill missing after install: ${skill}"
    fi
done

finish_success "REQUIRED skills setup complete"
suggest "NEXT STEPS / SUGGESTED ACTIONS:"
suggest "  1. Restart Claude Code, then run /help to confirm code-review and simplify are listed"
suggest "  2. Continue with 03_setup_required_plugins.sh"
resolve "RESOLUTION:"
resolve "  ls \"${CLAUDE_HOME}/skills\""
resolve "  head -n 4 \"${CLAUDE_HOME}/skills/code-review/SKILL.md\""

#!/usr/bin/env bash
# ============================================================
# Nexus Cove - OPTIONAL skills
# Writes fewer-permission-prompts and workflow-authoring as
# user-level SKILL.md files and verifies them.
# ============================================================
set -Eeuo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
init_log optional_skills

write_skill fewer-permission-prompts <<'EOF'
---
name: fewer-permission-prompts
description: Reduce repeated permission prompts by proposing narrow allow rules for safe, read-only commands. Use when the user keeps approving the same harmless commands.
---

# Fewer permission prompts

1. Identify the commands the user approved repeatedly in this session or in the logs.
2. Propose narrow allow rules only for read-only, low-risk commands, such as `git status`, `git diff`, `git log`, `ls`, `python -m pytest`, `python -m ruff check`, and `python -m compileall`.
3. Never propose allow rules for `rm`, `sudo`, `git push`, `git reset`, `curl` or `wget` piped to a shell, or anything that writes outside the project.
4. Show the exact `permissions.allow` JSON entries and wait for the user's approval before writing them to `.claude/settings.json`.
EOF

write_skill workflow-authoring <<'EOF'
---
name: workflow-authoring
description: Turn a multi-step task the user repeats into a reusable skill with a clear SKILL.md. Use when the user asks to save, reuse, or automate a workflow.
---

# Workflow authoring

1. Confirm the task, its inputs, its outputs, and how success is checked.
2. Write the steps in order, with exact commands and file paths.
3. Add a "Done when" section with one concrete verification step.
4. Save it as `~/.claude/skills/<name>/SKILL.md`. The frontmatter needs a name and a description that says when to use the skill.
5. Test the skill once on a real example before calling it finished.
EOF

for skill in fewer-permission-prompts workflow-authoring; do
    if skill_present "$skill"; then
        success "Verified skill present: ${skill}"
    else
        finish_failure "Skill missing after install: ${skill}"
    fi
done

warn "Not defined by this installer: Explore, loop, update-config. Check them inside Claude Code with /help or /agents."

finish_success "OPTIONAL skills setup complete"
suggest "NEXT STEPS / SUGGESTED ACTIONS:"
suggest "  1. Restart Claude Code and confirm the new skills appear in /help"
suggest "  2. Continue with 05_setup_optional_plugins.sh"
resolve "RESOLUTION:"
resolve "  ls \"${CLAUDE_HOME}/skills\""

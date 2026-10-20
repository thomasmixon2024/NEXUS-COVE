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

write_skill claude-api <<'EOF'
---
name: claude-api
description: Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration.
---

# claude-api Skill

Reference for the Claude API / Anthropic SDK — model ids, pricing, params, streaming, tool use, MCP, agents, caching, token counting, model migration.
TRIGGER — read BEFORE opening the target file; don't skip because it "looks like a one-liner" — whenever: the prompt names Claude/Anthropic in any form (Claude, Anthropic, Fable, Opus, Sonnet, Haiku, `anthropic`, `@anthropic-ai`, `claude-*`, `us.anthropic.*`, `[1m]`); the user asks about an LLM (pricing/model choice/limits/caching) — never answer from memory; OR the task is LLM-shaped with provider unstated (agent/MCP/tool-definition/multi-agent/RAG/LLM-judge/computer-use; generate/summarize/extract/classify/rewrite/converse over NL; debugging refusals/cutoffs/streaming/tool-calls/tokens).
SKIP only when another provider is being worked on (overrides all triggers): OpenAI/GPT/Gemini/Llama/Mistral/Cohere/Ollama named in the query; OR `grep -rE 'openai|langchain_openai|google.generativeai|genai|mistralai|cohere|ollama'` over the project hits (run this grep FIRST if no provider named — don't Read the file).
EOF

write_skill dataviz <<'EOF'
---
name: dataviz
description: Use this skill whenever you are about to create ANY chart, graph, plot, dashboard, or data visualization, in ANY output medium.
---

# dataviz Skill

Use this skill whenever you are about to create ANY chart, graph, plot, dashboard, or data visualization, in ANY output medium — an HTML or React artifact, inline SVG, plotting code in any library (matplotlib, plotly, d3, Recharts, …), an image/PNG you will render and upload, or a chart shared into Slack. Read it BEFORE writing the first line of chart code, choosing chart colors, building a stat tile / meter / KPI row, or laying out a dashboard. When the destination is a first-party document connector (host-designated, never self-described) that renders live charts, hand it the rows (inline, or as an uploaded data file the chart cites) rather than a rendered PNG/SVG — a picture of a chart loses hover, data inspection and per-value comments. Produces visualizations that read as one system — elegant, accessible, consistent in light and dark — using a brand-neutral placeholder palette you swap for your own. Teaches a design-system-agnostic method: a form heuristic, a color formula with a runnable validator, mark specs, and interaction rules. A validated default palette is documented in `references/palette.md` — swap that file's values for your brand's. Triggers on: "chart", "graph", "plot", "data viz", "visualization", "dashboard", "analytics", "visualize data", "categorical colors", "sequential / diverging palette", "stat tile", "sparkline", "heatmap", "legend", "axis", "tooltip", "chart colors", "color by series".
EOF

write_skill init <<'EOF'
---
name: init
description: Initialize a new CLAUDE.md file with codebase documentation
---

# init Skill

Initialize a new CLAUDE.md file with codebase documentation
EOF

write_skill keybindings-help <<'EOF'
---
name: keybindings-help
description: Use when the user wants to customize keyboard shortcuts, rebind keys, add chord bindings, or modify ~/.claude/keybindings.json.
---

# keybindings-help Skill

Use when the user wants to customize keyboard shortcuts, rebind keys, add chord bindings, or modify ~/.claude/keybindings.json. Examples: "rebind ctrl+s", "add a chord shortcut", "change the submit key", "customize keybindings".
EOF

write_skill plugin-authoring <<'EOF'
---
name: plugin-authoring
description: Make a mod: a change to Claude's own interface or behaviour, such as a live pane or panel, a band above the prompt, a status line, a toast, a slash command, or a hook on tool calls or prompts.
---

# plugin-authoring Skill

Make a mod: a change to Claude's own interface or behaviour, such as a live pane or panel, a band above the prompt, a status line, a toast, a slash command, or a hook on tool calls or prompts. Use to make, change or debug a mod or its hooks module.
EOF

write_skill run <<'EOF'
---
name: run
description: Launch and drive this project's app to see a change working. Use when asked to run, start, or screenshot the app, or to confirm a change works in the real app (not just tests).
---

# run Skill

Launch and drive this project's app to see a change working. Use when asked to run, start, or screenshot the app, or to confirm a change works in the real app (not just tests). First looks for a project skill that already covers launching the app; otherwise falls back to built-in patterns per project type (CLI, server, TUI, Electron, browser-driven, library).
EOF

write_skill security-review <<'EOF'
---
name: security-review
description: Complete a security review of the pending changes on the current branch
---

# security-review Skill

Complete a security review of the pending changes on the current branch
EOF

write_skill project-context <<'EOF'
---
name: project-context
description: Load Nexus Cove project context — architecture, ADRs, common commands, and key files. Use at session start or when context is lost.
---

# Project Context Loader

## On Invocation
1. Read and summarize: CLAUDE.md (project instructions)
2. Read and summarize: docs/architecture/overview.md
3. List: docs/decisions/ADR-*.md (titles + one-line summaries)
4. Show: Common dev commands from CLAUDE.md
5. Show: Key entry points (manager, worker, server)
6. Show: Test commands and Definition of Done checklist

## Output Format
Concise briefing — what to work on, key constraints, how to run tests.
EOF

for skill in fewer-permission-prompts workflow-authoring claude-api dataviz init keybindings-help plugin-authoring run security-review project-context; do
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
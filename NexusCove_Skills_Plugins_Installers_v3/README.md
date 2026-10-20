# Nexus Cove Skills, Plugins, and Chromium Installers (v3)

Each script installs and verifies its piece. The v2 scripts only wrote reference files.

| Script | What it does |
|---|---|
| `01_install_chromium.sh` | Installs Chromium (Termux `pkg` or Debian/Ubuntu `apt-get`), runs a headless render test, writes `claude_chromium_config/chromium.env`, and exports `CHROME_BIN` in `~/.bashrc` and `~/.zshrc` if they exist. |
| `02_setup_required_skills.sh` | Writes `code-review` and `simplify` as user skills in `~/.claude/skills/` and verifies them. |
| `03_setup_required_plugins.sh` | Installs `superpowers@claude-plugins-official` with `claude plugin install`, enables it in user and project settings, and verifies it. |
| `04_setup_optional_skills.sh` | Writes **11 optional skills** (4 original + 7 project-local + 1 new `project-context`) and verifies them. |
| `05_setup_optional_plugins.sh` | Installs anything listed in `OPTIONAL_PLUGINS`. The list is empty. |
| `run_all.sh` | Runs 01 through 05 in order and stops at the first failure. |
| `common.sh` | Shared helpers. Not run directly. |

## Required Skills (2)

- `code-review` — Review code changes for correctness, safety, definition-of-done
- `simplify` — Simplify recently changed code for reuse, clarity, efficiency

## Required Plugin (1)

- `superpowers@claude-plugins-official` — 15 process skills: `brainstorming`, `systematic-debugging`, `test-driven-development`, `writing-plans`, `executing-plans`, `verification-before-completion`, `subagent-driven-development`, `dispatching-parallel-agents`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `using-git-worktrees`, `using-superpowers`, `diagnosing-superpowers`, `writing-skills`

## Optional Skills (11)

| Skill | Description |
|-------|-------------|
| `project-context` | Load Nexus Cove project context: architecture, ADRs, commands, key files |
| `dataviz` | Design-system-agnostic data visualization (palette validator, mark specs) |
| `claude-api` | Claude API/SDK reference: models, pricing, streaming, tools, MCP, caching |
| `run` | Launch and drive the project app to verify changes |
| `security-review` | Security review checklist for pending changes |
| `plugin-authoring` | Create Claude Code mods: panes, status lines, toasts, slash commands, hooks |
| `init` | Initialize a new CLAUDE.md with codebase documentation |
| `keybindings-help` | Customize keyboard shortcuts in `~/.claude/keybindings.json` |
| `fewer-permission-prompts` | Reduce repeated permission prompts with narrow allow rules |
| `workflow-authoring` | Turn repeated multi-step tasks into reusable skills |
| `code-review` | Also available as required skill |

## Optional Plugins (0)

None defined by default. Add plugin IDs to `OPTIONAL_PLUGINS` array in `05_setup_optional_plugins.sh`.

## Requirements

- `python3` (used to edit `settings.json` safely)
- Claude Code CLI on PATH: `npm install -g @anthropic-ai/claude-code`
- Termux (`pkg`) or Debian/Ubuntu (`apt-get` with sudo or root)

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CLAUDE_HOME` | `~/.claude` | Where user skills and `settings.json` live |
| `NEXUS_COVE_ROOT` | `~/NEXUS-COVE` | Project root. Project-level settings and skills are used if it exists. |

## Run

```bash
cd NexusCove_Skills_Plugins_Installers_v3
chmod +x *.sh
./run_all.sh
```

Or run one step at a time: `./01_install_chromium.sh`, then `./02_...`, and so on.

## Notes

- Every run writes a timestamped log to `Logs/`. Settings files are backed up before they are changed.
- Existing skills are never overwritten. If a skill with the same name exists at user or project level, it is left alone.
- `general-purpose` and `Plan` are built-in agent types, not installable files. Check them with `/agents` in Claude Code.
- `Explore`, `loop`, and `update-config` are not defined by this installer. Check them with `/help`.
- On Ubuntu, the `chromium` package may be a snap wrapper that fails in containers and proot. The installer warns when it detects this.

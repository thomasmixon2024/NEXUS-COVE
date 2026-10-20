# Setup-ClaudeCodeCapabilities.ps1
# This script demonstrates how to use Claude Code's built-in skills, tools, and agents
# when working on the NEXUS COVE project.
# NOTE: These are built-in Claude Code capabilities - no external download/install needed

Write-Host "=== NEXUS COVE - Claude Code Capabilities Guide ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: The following are BUILT-IN Claude Code capabilities."
Write-Host "They do NOT require external download, build, or install."
Write-Host "They are accessed directly within Claude Code sessions."
Write-Host ""

Write-Host "=== CLAUDE CODE SKILLS ===" -ForegroundColor Green
Write-Host("These are invoked with: /<skill-name> or via the Skill tool")
Write-Host ""

$skills = @(
    @{Name="Plan"; Description="Software architect agent for designing implementation strategies"},
    @{Name="Explore"; Description="Read-only search agent for broad fan-out searches"},
    @{Name="general-purpose"; Description="For researching complex questions and executing multi-step tasks"},
    @{Name="claude-code-guide"; Description="Helpful for questions about Claude Code features"},
    @{Name="claude-api"; Description="Reference for Claude API/Anthropic SDK usage"},
    @{Name="dataviz"; Description="Useful for creating monitoring dashboards/visualizations"},
    @{Name="workflow-authoring"; Description="Important for creating/testing workflow scripts (NEXUS COVE is orchestration framework)"},
    @{Name="plugin-authoring"; Description="For extending Claude Code interface/behavior"},
    @{Name="fewer-permission-prompts"; Description="Reduce friction during development"},
    @{Name="update-config"; Description="For configuring Claude Code harness via settings.json"},
    @{Name="security-review"; Description="Review security implications of changes"}
)

foreach ($skill in $skills) {
    Write-Host ("/{0}: {1}" -f $skill.Name, $skill.Description) -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== CLAUDE CODE AGENT TYPES ===" -ForegroundColor Green
Write-Host("These are accessed via the Agent tool")
Write-Host ""

$agents = @(
    @{Name="claude"; Description="Catch-all for any task that doesn't fit a more specific agent"},
    @{Name="claude-code-guide"; Description="For questions about Claude Code, Claude Agent SDK, Claude API"},
    @{Name="Explore"; Description="Read-only search agent for broad fan-out searches"},
    @{Name="general-purpose"; Description="General-purpose agent for researching complex questions"},
    @{Name="Plan"; Description="Software architect agent for designing implementation plans"},
    @{Name="statusline-setup"; Description="Configure user's Claude Code status line setting"}
)

foreach ($agent in $agents) {
    Write-Host ("{0}: {1}" -f $agent.Name, $agent.Description) -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== CLAUDE CODE TOOLS (used programmatically) ===" -ForegroundColor Green
Write-Host("These are used by Claude Code agents via the Tool interface")
Write-Host ""

$tools = @(
    @{Name="code-review"; Description="Review current diff or PR for correctness bugs and cleanups"},
    @{Name="simplify"; Description="Review code for reuse, simplification, efficiency"},
    @{Name="workflow-authoring"; Description="Reference for writing Workflow tool scripts"},
    @{Name="plugin-authoring"; Description="Make mods to Claude's interface or behaviour"},
    @{Name="fewer-permission-prompts"; Description="Scan transcripts to add allowlist to reduce permission prompts"},
    @{Name="update-config"; Description="Configure Claude Code harness via settings.json"},
    @{Name="security-review"; Description="Complete security review of pending changes"},
    @{Name="run"; Description="Launch and drive NEXUS COVE app to see changes working"}
)

foreach ($tool in $tools) {
    Write-Host ("{0}: {1}" -f $tool.Name, $tool.Description) -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== HOW TO USE THESE IN NEXUS COVE DEVELOPMENT ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. To use a SKILL in Claude Code chat:" -ForegroundColor Green
Write-Host "   /Plan"
Write-Host "   /Explore <search query>"
Write-Host "   /fewer-permission-prompts"
Write-Host ""

Write-Host "2. To invoke an AGENT:" -ForegroundColor Green
Write-Host "   Agent tool with subagent_type: 'Plan' (for architectural planning)"
Write-Host "   Agent tool with subagent_type: 'Explore' (for broad searches)"
Write-Host "   Agent tool with subagent_type: 'general-purpose' (for multi-step tasks)"
Write-Host ""

Write-Host "3. Examples of using SKILLS with NEXUS COVE:" -ForegroundColor Green
Write-Host "   /Plan          # Then describe: 'Design enhanced agent communication protocols'"
Write-Host "   /Explore       # Then ask: 'How is WebSocket transport implemented in NexusCove?'"
Write-Host "   /workflow-authoring  # Before creating workflow scripts"
Write-Host "   /dataviz       # Before creating monitoring dashboards"
Write-Host ""

Write-Host "4. To reduce permission prompts during development:" -ForegroundColor Green
Write-Host "   /fewer-permission-prompts"
Write-Host "   (This scans your transcripts and adds common read-only operations to .claude/settings.json)"
Write-Host ""

Write-Host "5. To configure Claude Code for NEXUS COVE development:" -ForegroundColor Green
Write-Host "   /update-config"
Write-Host "   (Then follow prompts to set up permissions, hooks, etc.)"
Write-Host ""

Write-Host "=== VERIFYING NEXUS COVE INSTALLATION ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To verify NEXUS COVE is properly set up:" -ForegroundColor Yellow
Write-Host "   python -m nexus_cove.transport.websocket.server  # Start local server"
Write-Host "   python -m nexus_cove.orchestration.manager       # Start manager"
Write-Host "   python -m nexus_cove.agents.worker --name Aegis-Worker --test-backend  # Start worker"
Write-Host ""
Write-Host "To run tests:" -ForegroundColor Yellow
Write-Host "   python -m pytest -q"
Write-Host "   python -m compileall -q src tests"
Write-Host "   python -m ruff check ."
Write-Host ""

Write-Host "=== SESSION CONTINUITY (already configured) ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "NEXUS COVE already has session continuity configured via:"
Write-Host "   .claude/initialize_session.py"
Write-Host "   (This runs automatically at start of each Claude Code session)"
Write-Host ""
Write-Host "To manually trigger session continuity check:"
Write-Host "   python .claude/initialize_session.py"
Write-Host ""

Write-Host "=== NEXT STEPS FOR NEXUS COVE DEVELOPMENT ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Based on the session continuity guide, consider:"
Write-Host "1. Updating README.md to document virtual environment setup process"
Write-Host "2. Creating launcher scripts that automatically use the virtual environment"
Write-Host "3. Testing enhanced agent memory system in actual agent interactions"
Write-Host "4. Validating masterkill scripts work correctly to stop all processes"
Write-Host "5. Creating terminal-based dashboard/chat interface for pwsh/Ubuntu Termux environments"
Write-Host ""

Write-Host "=== SUMMARY ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ No external downloads/builds/installs needed for Claude Code capabilities"
Write-Host "✓ All skills/tools/agents are built into Claude Code"
Write-Host "✓ Access them via commands like /Plan, /Explore, or via Agent tool"
Write-Host "✓ NEXUS COVE already has excellent session continuity configured"
Write-Host "✓ Focus on actual NEXUS COVE development rather than setup"
Write-Host ""
Write-Host "To get started developing NEXUS COVE:" -ForegroundColor Green
Write-Host "1. Launch Claude Code in the NEXUS COVE directory"
Write-Host "2. Use /Plan to design your implementation approach"
Write-Host "3. Use /Explore to search the codebase"
Write-Host "4. Use Agent tool to spawn specialized agents when needed"
Write-Host ""
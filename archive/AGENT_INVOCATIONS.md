# NEXUS-COVE Agent Invocations (Qwen2.5:0.5b Optimized)

This document contains specialized agent invocation patterns for the NEXUS-COVE repository, optimized for use with the `qwen2.5:0.5b` Ollama model that the repository employs for agent-to-agent chat replies.

## Purpose

These invocations provide **role-specific guidance** for getting specialized behavior from your Ollama-hosted model when working with the NEXUS-COVE codebase. They complement (but do not replace) the existing agent system based on TOML personality files.

## Available Agent Invocations

Each invocation is designed to elicit specific behaviors from the `qwen2.5:0.5b` model when working with NEXUS-COVE:

### 1. Nexus Architect
**Role**: Architecture planner for NEXUS COVE changes  
**Source**: Based on `.github/prompts/nexus-architect.prompt.md`  
**Best For**: Architectural decisions, subsystem allocation, design reviews

### 2. Nexus Debug  
**Role**: Root-cause debugging specialist for runtime issues  
**Source**: Based on `.github/prompts/nexus-debug.prompt.md`  
**Best For**: Bug investigation, failure analysis, debugging complex issues

### 3. Nexus Docs/Ops
**Role**: Documentation and operations specialist  
**Source**: Based on `.github/prompts/nexus-docs-ops.prompt.md`  
**Best For**: Documentation updates, procedure validation, release notes

### 4. Nexus Validator
**Role**: Validation and regression checker  
**Source**: Based on `.github/prompts/nexus-validator.prompt.md`  
**Best For**: Testing verification, validation protocols, evidence-based conclusions

## Usage Instructions

### Prerequisites
1. Ollama installed and running locally (`ollama serve`)
2. `qwen2.5:0.5b` model downloaded (`ollama pull qwen2.5:0.5b`)
3. Basic familiarity with prompting Ollama models

### Basic Invocation Pattern
```bash
ollama run qwen2.5:0.5b << 'EOF'
[PASTE THE COMPLETE AGENT INVOCATION HERE]

[YOUR SPECIFIC QUESTION OR TASK HERE]
EOF
```

### Example Usage
To get architectural guidance on a potential change:
```bash
ollama run qwen2.5:0.5b << 'EOF'
You are now acting as the Nexus Architect agent for the NEXUS COVE system.

[PASTE THE COMPLETE NEXUS-ARCHITECT AGENT DEFINITION HERE]

I'm considering adding a new feature to the WebSocket transport layer. What subsystem should this work belong to, and what is the minimal correct design that matches the existing architecture?
EOF
```

## Agent Definition Files

For the complete agent definitions optimized for `qwen2.5:0.5b`, see the individual files:

- **Nexus Architect**: `./agent-invocations/nexus-architect/AGENT.md`
- **Nexus Debug**: `./agent-invocations/nexus-debug/AGENT.md`  
- **Nexus Docs/Ops**: `./agent-invocations/nexus-docs-ops/AGENT.md`
- **Nexus Validator**: `./agent-invocations/nexus-validator/AGENT.md`

## Integration with Existing NEXUS-COVE Agents

These invocations **complement** the existing agent system:

| Aspect | Existing Agents (TOML-based) | These Invocations |
|--------|------------------------------|-------------------|
| **Basis** | TOML personality files (`Aegis-Worker.toml`, etc.) | Role-specific prompts from GitHub |
| **Agents** | Aegis (careful), Vigil (playful), Elon (first-principles) | Architect, Debug, Docs/Ops, Validator |
| **Focus** | How agents behave/personality | What agents should do/role-specific guidance |
| **Usage** | Built into agent worker startup | Manual prompting for specialized tasks |
| **Model** | Can use `--model qwen2.5:0.5b` flag | Direct Ollama prompting |

### Recommended Workflow
1. Use existing agents (`Aegis-Worker`, `Vigil-Worker`, `Elon-Worker`) for general development via `python -m nexus_cove.agents.worker`
2. Use these specialized invocations when you need focused, role-specific guidance for particular tasks
3. Combine approaches: Run general agents for baseline behavior, then use specialized invocations for deep dives

## Deployment Notes

These files are designed to be lightweight additions that won't interfere with the existing NEXUS-COVE agent system. They can be safely added to any clone of the repository.

## Maintenance

Update these invocations when:
1. The GitHub prompt files change significantly
2. You discover more effective ways to elicit specific behaviors from `qwen2.5:0.5b`
3. The NEXUS-COVE codebase evolves in ways that affect these role-specific needs

The core NEXUS-COVE agent system (`/src/nexus_cove/agents/`) should remain unchanged unless making modifications to the repository itself.
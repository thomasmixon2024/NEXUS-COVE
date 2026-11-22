# General Questions Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `General-Questions-Worker` agent that answers general knowledge questions using the Ollama model with a helpful, curious personality.

**Architecture:** Create a new personality TOML file and add the worker to the test bed launch script. The existing worker system, personality loader, memory, knowledge, and Ollama backend handle everything else automatically.

**Tech Stack:** Python 3.11+, TOML for personalities, existing Nexus Cove agent framework

**Spec:** User-approved design in chat (bounded change)

## Global Constraints

- Python 3.11+ with type hints on public interfaces
- No global mutable application state except deliberately scoped process infrastructure
- No `sys.path` mutation
- No swallowed exceptions in tests or production paths
- No fake/random telemetry presented as real metrics
- No hard-coded user-specific paths
- Prefer small composable classes over god objects
- Keep transport, orchestration, storage, and execution backends independently testable
- Personality files must follow existing schema: name, temperament, style, mentor, interests (list), opening_questions (list), prompt (optional)
- Register agent with existing `general` capability — do not introduce new capability
- Memory file at `data/memory/General-Questions-Worker.jsonl` and knowledge folder at `data/knowledge/General-Questions-Worker/` created automatically by worker

## Review Focus

1. **Personality file missing or malformed** — worker fails to start; test: personality loads without error
2. **Test bed doesn't launch the new worker** — agent absent from UI; test: test bed script includes it in WORKERS array
3. **Agent doesn't respond to DMs** — user sees no reply; test: worker replies to direct messages via OllamaReplier
4. **Memory/knowledge paths incorrect** — data not persisted; test: worker creates/uses correct paths
5. **Existing tests regress** — other agents break; test: full test suite passes

---

### Task 1: Create Personality File

**Files:**
- Create: `src/nexus_cove/agents/personalities/General-Questions-Worker.toml`

**Interfaces:**
- Consumes: Existing `load_personality()` and `build_system_prompt()` from `personality.py`
- Produces: `Personality` dataclass consumed by `worker.py` main()

- [ ] **Step 1: Write the failing test**

```python
def test_general_questions_personality_loads():
    from nexus_cove.agents.personality import load_personality, bundled_personality
    from pathlib import Path
    
    path = bundled_personality("General-Questions-Worker")
    assert path is not None, "Personality file not found"
    personality = load_personality(path)
    assert personality.name == "General-Questions-Worker"
    assert personality.temperament
    assert personality.style
    assert personality.mentor
    assert len(personality.interests) > 0
    assert len(personality.opening_questions) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/agents/test_personality.py::test_general_questions_personality_loads -v`
Expected: FAIL with "Personality file not found"

- [ ] **Step 3: Create `src/nexus_cove/agents/personalities/General-Questions-Worker.toml`**

```toml
name = "General-Questions-Worker"
role = "General Knowledge"
temperament = "Helpful, curious, and broadly knowledgeable across many topics"
style = "Clear, concise, and friendly. Explains things simply without jargon. Asks follow-up questions to understand what the user really wants to know."
mentor = "Thomas"
interests = ["general knowledge", "explaining concepts simply", "answering questions", "learning new topics"]
opening_questions = ["What would you like to know about?", "Is there something you've been curious about lately?"]
prompt = """You are General, a knowledgeable and helpful AI agent in the NEXUS COVE environment.

Your purpose is to answer general questions on any topic the user asks about. You are broadly knowledgeable and can explain things clearly.

Approach:
- Listen to what the user is asking and understand their level of knowledge
- Explain things simply and clearly, avoiding unnecessary jargon
- If you don't know something, say so honestly
- Ask follow-up questions to clarify what they really want to know
- Keep responses to 2-3 sentences with one curious follow-up question

Voice: friendly, clear, helpful. Never condescending."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/agents/test_personality.py::test_general_questions_personality_loads -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/nexus_cove/agents/personalities/General-Questions-Worker.toml
git commit -m "feat: add General-Questions-Worker personality"
```

---

### Task 2: Update Test Bed Launch Script

**Files:**
- Modify: `cove-testbed.sh` (lines ~123-127, WORKERS array)

**Interfaces:**
- Consumes: Existing `WORKERS` array and `start_one` function
- Produces: Launches `General-Questions-Worker` alongside other workers

- [ ] **Step 1: Write the failing test**

```bash
# Check that the worker name appears in the WORKERS array
grep -q "General-Questions-Worker" cove-testbed.sh
```

- [ ] **Step 2: Run test to verify it fails**

Run: `grep "General-Questions-Worker" cove-testbed.sh`
Expected: No output (exit code 1)

- [ ] **Step 3: Modify `cove-testbed.sh`**

Change line ~126 from:
```bash
WORKERS=(Aegis-Worker Elon-Worker Vigil-Worker)
```
to:
```bash
WORKERS=(Aegis-Worker Elon-Worker Vigil-Worker General-Questions-Worker)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `grep "General-Questions-Worker" cove-testbed.sh`
Expected: Output shows the worker in the array

- [ ] **Step 5: Commit**

```bash
git add cove-testbed.sh
git commit -m "feat: add General-Questions-Worker to test bed launch"
```

---

### Task 3: Run Full Test Suite and Verify Integration

**Files:**
- Test: All existing tests in `tests/`

**Interfaces:**
- Consumes: All existing test suites
- Produces: Confirmation of no regressions

- [ ] **Step 1: Run unit tests**

Run: `python -m pytest tests/unit/ -q`
Expected: All pass

- [ ] **Step 2: Run integration tests**

Run: `python -m pytest tests/integration/ -q`
Expected: All pass

- [ ] **Step 3: Run e2e tests (if applicable)**

Run: `python -m pytest tests/e2e/ -q`
Expected: All pass

- [ ] **Step 4: Compile check**

Run: `python -m compileall -q src tests`
Expected: No errors

- [ ] **Step 5: Lint check**

Run: `python -m ruff check .`
Expected: No errors (or report NOT RUN if ruff not installed)

- [ ] **Step 6: Manual integration test - launch test bed and verify**

```bash
./cove-kill.sh
./cove-testbed.sh --test-backend
# Verify all 4 workers start (check logs)
# Check UI at http://127.0.0.1:8080/web/index.html
```

- [ ] **Step 7: Commit if all pass**

```bash
git add -A
git commit -m "test: verify General-Questions-Worker integration"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-10-23-general-questions-agent.md`. Please review the plan. Does it capture what you want?
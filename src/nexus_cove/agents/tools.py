"""Agent tools.

Each tool is a small, self-contained capability assigned to an agent
via ``toolkit_for``. Tools read from a message and return either a
short report string or ``None`` if the message does not trigger them.
"""

from __future__ import annotations

import ast
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nexus_cove.agents.memory import AgentMemory


class DebugAssistant:
    """Explains Python exceptions and tracebacks found in a message."""

    name = "Debug Assistant"

    _TRIGGERS = (
        "traceback", "trace back", "exception", "error", "failed",
        "TypeError", "ValueError", "KeyError", "IndexError",
        "AttributeError", "NameError", "ImportError", "RuntimeError",
        "raise", "caught", "stack trace", "crash",
    )

    _HINTS = {
        "TypeError": "Wrong type passed, or calling something on None. Check the arguments to the function that raised.",
        "ValueError": "Right type, wrong value. Check the content — empty string, bad format, out of range.",
        "KeyError": "Dict lookup failed. The key does not exist. Use .get() with a default, or check membership first.",
        "IndexError": "List/tuple index out of range. Check len() before indexing.",
        "AttributeError": "The object does not have that attribute. Usually None when it should not be — check what was returned.",
        "NameError": "A name was used before it was assigned or imported. Check typos, missing imports, or scope.",
        "ImportError": "A module or name could not be imported. Check it is installed, spelled correctly, and on the path.",
        "ModuleNotFoundError": "The module is not installed or not on sys.path.",
        "RuntimeError": "The code ran but hit a runtime condition. The exception message usually names the specific issue.",
        "FileNotFoundError": "The file path is wrong or the file does not exist. Check the working directory.",
        "RecursionError": "No reachable base case. Add one, or convert to iteration.",
    }

    def run(self, text: str) -> str | None:
        lowered = text.lower()
        if not any(t.lower() in lowered for t in self._TRIGGERS):
            return None

        exc_match = re.search(r"(\w+(?:Error|Exception))\s*:\s*(.+?)(?:\n|$)", text)
        if not exc_match:
            return (
                "Debug Assistant: I see error keywords but no exception class. "
                "Paste the full traceback ending in `ExceptionName: message` "
                "so I can identify the type and the last frame."
            )

        exc_type = exc_match.group(1)
        exc_msg = exc_match.group(2).strip()
        hint = self._HINTS.get(
            exc_type,
            "Read the exception message and the last frame in the traceback — that is where the failure is.",
        )

        frames = re.findall(r'File "([^"]+)", line (\d+), in (\S+)', text)
        last_frame = ""
        if frames:
            f, ln, fn = frames[-1]
            last_frame = f"\n- Last frame: {f}:{ln} in {fn}()"

        return (
            f"Debug Assistant:\n"
            f"- Exception: {exc_type}: {exc_msg}\n"
            f"- Meaning: {hint}"
            f"{last_frame}\n"
            f"- Next: reproduce with the smallest possible input, then fix the cause, not the symptom."
        )


class DevAssistant:
    """Analyzes Python code structure, unused imports, missing docstrings, complexity."""

    name = "Dev Assistant"

    _TRIGGERS = (
        "review", "refactor", "improve", "analyze", "check this code",
        "unused import", "unused imports", "undefined", "linter",
        "static analysis", "code quality", "complexity", "docstring",
    )

    def run(self, text: str) -> str | None:
        lowered = text.lower()
        code = self._extract_code(text)

        if code is None:
            if not any(t in lowered for t in self._TRIGGERS):
                return None
            return (
                "Dev Assistant: no Python code block found. "
                "Paste code between ```python and ``` so I can analyze it."
            )

        return self._analyze(code)

    def _extract_code(self, text: str) -> str | None:
        match = re.search(r"```(?:python)?\n(.*?)\n```", text, re.DOTALL)
        return match.group(1) if match else None

    def _analyze(self, code: str) -> str:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return (
                f"Dev Assistant:\n"
                f"- SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}\n"
                f"- Fix the syntax first — nothing else can be analyzed until it parses."
            )

        lines = ["Dev Assistant:"]
        issues = 0

        imported = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported[alias.asname or alias.name.split(".")[0]] = node.lineno
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        imported[alias.asname or alias.name] = node.lineno

        used_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        unused = [name for name in imported if name not in used_names]
        if unused:
            issues += 1
            lines.append(f"- Unused imports: {', '.join(sorted(unused))}")

        defined = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                has_doc = ast.get_docstring(node) is not None
                defined.append(
                    f"def {node.name} (line {node.lineno})"
                    + ("" if has_doc else " [no docstring]")
                )
            elif isinstance(node, ast.ClassDef):
                has_doc = ast.get_docstring(node) is not None
                defined.append(
                    f"class {node.name} (line {node.lineno})"
                    + ("" if has_doc else " [no docstring]")
                )
        if defined:
            lines.append(f"- Defined: {', '.join(defined)}")

        missing_docs = sum(1 for d in defined if "[no docstring]" in d)
        if missing_docs:
            issues += 1
            lines.append(
                f"- Missing docstrings: {missing_docs} of {len(defined)} definitions"
            )

        complex_funcs = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                branches = sum(
                    1
                    for n in ast.walk(node)
                    if isinstance(
                        n, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp)
                    )
                )
                if branches >= 6:
                    complex_funcs.append(f"{node.name} ({branches} branches)")
        if complex_funcs:
            issues += 1
            lines.append(
                f"- Complex functions (>=6 branches): {', '.join(complex_funcs)}"
            )

        if issues == 0:
            lines.append(
                "- No unused imports, no missing docstrings, no high complexity found."
            )
        return "\n".join(lines)


class FirstPrinciplesAssistant:
    """Analyzes problems from a first-principles perspective, identifying
    fundamental constraints, engineering bottlenecks, and optimization
    opportunities at the level of physics and production efficiency.

    Triggers on keywords related to first-principles thinking, constraint
    analysis, and orders-of-magnitude evaluation — consistent with
    Elon-Worker's temperament: "first-principles driven, relentlessly
    fast-paced, and intensely focused on physics, engineering bottlenecks,
    and the expansion of consciousness."
    """

    name = "First Principles Assistant"

    _TRIGGERS = frozenset(
        {
            "first principles",
            "fundamental",
            "constraint",
            "constraints",
            "bottleneck",
            "bottlenecks",
            "optimize",
            "orders of magnitude",
            "physics",
            "engineering",
            "production loop",
            "multi-planetary",
            "assumptions",
            "core constraint",
            "essential constraint",
        }
    )

    def run(self, text: str) -> str | None:
        lowered = text.lower()
        if not any(t in lowered for t in self._TRIGGERS):
            return None

        # Identify trigger keywords and provide a first-principles analysis.
        lines: list[str] = []

        # Look for "orders of magnitude" estimates
        if "orders of magnitude" in lowered:
            lines.append(
                "- First principles: Estimate the dominant term and scale it."
            )

        # Look for constraint-related queries
        if "constraint" in lowered or "constraints" in lowered:
            lines.append(
                "- First principles: Identify the physical or resource constraints "
                "that cannot be violated."
            )

        # Look for bottleneck-related queries
        if "bottleneck" in lowered or "bottlenecks" in lowered:
            lines.append(
                "- First principles: The bottleneck is the narrowest point in the "
                "system flow — widening it elsewhere has diminishing returns."
            )

        # Look for fundamental/physics queries
        if "physics" in lowered or "fundamental" in lowered:
            lines.append(
                "- First principles: Strip away every layer of engineering convention "
                "and ask: what does nature actually allow or demand?"
            )

        # Look for production/engineering optimization
        if "engineering" in lowered or "production" in lowered or "loop" in lowered:
            lines.append(
                "- First principles: Reduce the problem to its essential variables, "
                "then rebuild from the simplest functional subset."
            )

        # Look for multi-planetary / expansion queries
        if "multi-planetary" in lowered or "expansion" in lowered:
            lines.append(
                "- First principles: The limiting factor is rarely technology — it is "
                "energy, material, or the physics of the destination environment."
            )

        if not lines:
            # Fallback: generic first-principles prompt
            lines.append(
                "- First principles: Go back to the most basic truths and reason up "
                "from there, discarding every assumption that is not known to be true."
            )

        return "\n".join(lines)


def toolkit_for(agent_id: str, memory: AgentMemory) -> tuple:
    """Return the tool tuple for ``agent_id``.

    Aegis-Worker is the Debugger. Vigil-Worker is the Developer.
    Elon-Worker is the First Principles thinker.
    """
    if agent_id == "Aegis-Worker":
        return (DebugAssistant(),)
    if agent_id == "Vigil-Worker":
        return (DevAssistant(),)
    if agent_id == "Elon-Worker":
        return (FirstPrinciplesAssistant(),)
    return ()
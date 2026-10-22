"""The two tools the agents asked for. Each returns real data or nothing.

- CodeAnalyzer (Aegis-Worker): detects syntax errors, unused imports,
  undefined names, and lists functions/classes in Python code snippets
  embedded in agent messages. Uses stdlib ast + tokenize only.
- PatternFinder (Vigil-Worker): counts words and questions in messages this
  agent has actually heard, from its own memory log.

A tool returns None when it has nothing to add, so it never adds noise.
"""

from __future__ import annotations

import ast
import builtins
import csv
import os
import re
import tokenize
from collections import Counter
from io import BytesIO
from pathlib import Path

from nexus_cove.agents.memory import AgentMemory

REFERENCE_DIR_ENV = "NEXUS_COVE_REFERENCE_DIR"
GEOLOGY_COLUMNS = ("material", "property", "value", "unit", "source")
PATTERN_TRIGGERS = ("pattern", "repeat", "most common", "how often", "trend")
MIN_MESSAGES_FOR_PATTERNS = 5
STOPWORDS = frozenset(
    "the and that with this what have from about would could should there their they your "
    "them were will just like into when than then some more been very also over only does "
    "know think being which where while would".split()
)

CODE_TRIGGERS = (
    "debug", "traceback", "error", "exception", "syntax", "stack trace",
    "TypeError", "ValueError", "NameError", "AttributeError"
)


def reference_dir() -> Path:
    return Path(os.environ.get(REFERENCE_DIR_ENV, "reference"))


class GeologyAnalyzer:
    name = "Geology Analyzer"

    def __init__(self, path: Path) -> None:
        self.path = path

    def _rows(self) -> list[dict]:
        if not self.path.is_file():
            return []
        with self.path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = set(GEOLOGY_COLUMNS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"{self.path.name} is missing columns: {sorted(missing)}")
            return [row for row in reader if (row.get("material") or "").strip()]

    def run(self, text: str) -> str | None:
        lowered = text.lower()
        hits = [row for row in self._rows() if row["material"].strip().lower() in lowered]
        if not hits:
            return None
        lines = [
            f"- {row['material']}: {row['property']} = {row['value']} {row['unit']} "
            f"(source: {row['source']})"
            for row in hits
        ]
        return "Geology Analyzer (from the reference file):\n" + "\n".join(lines)


class CodeAnalyzer:
    name = "Code Analyzer"

    def __init__(self) -> None:
        pass

    def _extract_code_block(self, text: str) -> str | None:
        """Extract Python code from fenced code blocks (```python ... ```)."""
        # Match ```python ... ``` or ``` ... ``` with or without trailing newline
        pattern = r'```(?:python)?\n(.*?)\n?```'
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[0]
        return None

    def _has_trigger(self, text: str) -> bool:
        """Check if message contains code block or trigger keywords."""
        if self._extract_code_block(text) is not None:
            return True
        lowered = text.lower()
        return any(trigger.lower() in lowered for trigger in CODE_TRIGGERS)

    def _get_defined_names(self, tree: ast.AST) -> set[str]:
        """Get all names defined in the module (functions, classes, imports, assignments)."""
        defined = set()

        # Built-ins
        defined.update(dir(builtins))

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defined.add(node.name)
                # Add function arguments
                for arg in node.args.args:
                    defined.add(arg.arg)
                for arg in node.args.kwonlyargs:
                    defined.add(arg.arg)
                if node.args.vararg:
                    defined.add(node.args.vararg.arg)
                if node.args.kwarg:
                    defined.add(node.args.kwarg.arg)
            elif isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    # Use the alias name (as imported) or the original name
                    if alias.asname:
                        defined.add(alias.asname)
                    else:
                        defined.add(alias.name.split('.')[0])
            elif isinstance(node, (ast.Assign, ast.AnnAssign)):
                # Handle simple assignments
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            defined.add(target.id)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    defined.add(node.target.id)

        return defined

    def _get_imported_names(self, tree: ast.AST) -> dict[str, str]:
        """Get imported names: alias -> original name."""
        imports = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name.split('.')[0]
                    imports[name] = alias.name
        return imports

    def _get_unused_imports(self, tree: ast.AST, imports: dict[str, str], defined_names: set[str]) -> list[str]:
        """Find unused imports."""
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                # attribute access like module.function
                pass  # We can't easily track these

        unused = []
        for alias_name, original_name in imports.items():
            # Check if the alias is used anywhere
            if alias_name not in used_names:
                # Also check if any part of the import is used
                # For "import foo.bar", check if "foo" is used
                root_name = original_name.split('.')[0]
                if root_name not in used_names:
                    unused.append(alias_name)
        return unused

    def _get_undefined_names(self, tree: ast.AST, defined_names: set[str]) -> list[str]:
        """Find potentially undefined names (best effort)."""
        undefined = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in defined_names:
                    undefined.add(node.id)

        return sorted(undefined)

    def _get_functions_and_classes(self, tree: ast.AST) -> list[str]:
        """Get list of functions and classes with line numbers."""
        items = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                items.append(f"def {node.name} (line {node.lineno})")
            elif isinstance(node, ast.ClassDef):
                items.append(f"class {node.name} (line {node.lineno})")
        return items

    def run(self, text: str) -> str | None:
        if not self._has_trigger(text):
            return None

        code = self._extract_code_block(text)
        if code is None:
            code = text

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"
        except Exception as e:
            return f"CodeAnalyzer could not analyze this input: {e}"

        try:
            imports = self._get_imported_names(tree)
            defined_names = self._get_defined_names(tree)
            unused = self._get_unused_imports(tree, imports, defined_names)
            undefined = self._get_undefined_names(tree, defined_names)
            functions_classes = self._get_functions_and_classes(tree)

            # Issues are only unused imports and undefined names
            has_issues = bool(unused or undefined)

            if not has_issues:
                func_count = len([n for n in functions_classes if n.startswith('def')])
                class_count = len([n for n in functions_classes if n.startswith('class')])
                return f"Code parsed cleanly. {func_count} function(s), {class_count} class(es). No unused imports or obvious undefined names detected."

            lines = []
            if unused:
                lines.append(f"- Unused imports: {', '.join(unused)}")
            if undefined:
                lines.append(f"- Potentially undefined names: {', '.join(undefined)}")
            if functions_classes:
                lines.append(f"- Defined: {', '.join(functions_classes)}")

            return "Code Analyzer:\n" + "\n".join(lines)
        except Exception as e:
            return f"CodeAnalyzer could not analyze this input: {e}"


class PatternFinder:
    name = "Pattern Finder"

    def __init__(self, memory: AgentMemory) -> None:
        self._memory = memory

    def run(self, text: str) -> str | None:
        if not any(trigger in text.lower() for trigger in PATTERN_TRIGGERS):
            return None
        heard = [
            entry["text"] for entry in self._memory.entries() if entry["direction"] == "received"
        ]
        if len(heard) < MIN_MESSAGES_FOR_PATTERNS:
            return (
                f"Pattern Finder: {len(heard)} message(s) heard so far; it needs "
                f"{MIN_MESSAGES_FOR_PATTERNS} before reporting patterns."
            )
        words = Counter(
            word
            for message in heard
            for word in re.findall(r"[a-z']+", message.lower())
            if len(word) >= 4 and word not in STOPWORDS
        )
        questions = sum(message.count("?") for message in heard)
        top = ", ".join(f"{word} ({count})" for word, count in words.most_common(5)) or "none"
        return (
            f"Pattern Finder (from {len(heard)} messages heard): most repeated words: {top}. "
            f"Questions heard: {questions}."
        )


def toolkit_for(agent_id: str, memory: AgentMemory) -> tuple:
    """Each agent gets only the tool it asked for."""
    if agent_id == "Aegis-Worker":
        return (CodeAnalyzer(),)
    if agent_id == "Vigil-Worker":
        return (PatternFinder(memory),)
    return ()

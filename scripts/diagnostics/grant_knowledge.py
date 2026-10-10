#!/usr/bin/env python3
"""Give one agent a document, or list what an agent holds.

Usage:
    python scripts\\diagnostics\\grant_knowledge.py Aegis-Worker notes.md
    python scripts\\diagnostics\\grant_knowledge.py Vigil-Worker --list

The document is copied into that agent's own folder, and no other agent
can read it. Only .md and .txt files are accepted.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from nexus_cove.agents.knowledge import EXTENSIONS, KnowledgeStore, knowledge_folder


def main() -> int:
    parser = argparse.ArgumentParser(description="Grant or list one agent's knowledge.")
    parser.add_argument("agent")
    parser.add_argument("file", nargs="?", help="document to give this agent")
    parser.add_argument("--list", action="store_true", help="list what this agent holds")
    parser.add_argument("--replace", action="store_true", help="overwrite an existing item")
    args = parser.parse_args()

    try:
        folder = knowledge_folder(args.agent)
    except ValueError as exc:
        print(f"[FAILURE] {exc}")
        return 2

    if args.list or not args.file:
        titles = sorted(KnowledgeStore(folder).items())
        print(f"{args.agent} holds {len(titles)} item(s):")
        for title in titles:
            print(f"  - {title}")
        return 0

    source = Path(args.file)
    if not source.is_file():
        print(f"[FAILURE] No such file: {source}")
        return 2
    if source.suffix.lower() not in EXTENSIONS:
        print(f"[FAILURE] Only {', '.join(EXTENSIONS)} files can be given.")
        return 2
    target = folder / source.name
    if target.exists() and not args.replace:
        print(f"[FAILURE] {args.agent} already holds {source.name}. Use --replace to overwrite.")
        return 2
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    print(f"[SUCCESS] {args.agent} now holds {source.stem}. No other agent can read it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

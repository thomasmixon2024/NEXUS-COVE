#!/usr/bin/env python3
"""Send one direct message to an agent and print its reply.

Usage:
    python scripts\\diagnostics\\ask_agent.py Aegis-Worker "What is a bee?"
    python scripts\\diagnostics\\ask_agent.py Vigil-Worker "hi" --as Thomas --timeout 60

Requires the server to be running. Exit codes: 0 = reply arrived, 1 = no reply
(timeout or silence), 2 = server or connection error.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import websockets


async def ask(uri: str, me: str, target: str, text: str, timeout: float) -> str | None:
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"version": 1, "action": "register", "username": me}))
        await asyncio.sleep(0.3)
        await ws.send(
            json.dumps(
                {
                    "version": 1,
                    "action": "direct_message",
                    "recipient": target,
                    "message": text,
                }
            )
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                return None
            try:
                frame = json.loads(await asyncio.wait_for(ws.recv(), remaining))
            except TimeoutError:
                return None
            if frame.get("action") == "direct_message" and frame.get("sender") == target:
                return frame.get("message", "")
            if frame.get("action") == "error":
                raise RuntimeError(str(frame.get("error")))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask one agent a question.")
    parser.add_argument("agent")
    parser.add_argument("message")
    parser.add_argument(
        "--as",
        dest="me",
        default="Diagnostic-Probe",
        help="name to register as; must not clash with a name already in use",
    )
    parser.add_argument("--uri", default="ws://127.0.0.1:8765")
    parser.add_argument("--timeout", type=float, default=45.0, help="seconds to wait")
    args = parser.parse_args()
    try:
        reply = asyncio.run(ask(args.uri, args.me, args.agent, args.message, args.timeout))
    except OSError as exc:
        print(f"[FAILURE] Cannot reach {args.uri}: {exc}")
        return 2
    except RuntimeError as exc:
        print(f"[FAILURE] Server refused the request: {exc}")
        return 2
    if reply is None:
        print(
            f"[NO REPLY] {args.agent} did not answer within {args.timeout:.0f}s "
            "(check the pause file and that the worker is running)."
        )
        return 1
    print(f"{args.agent}: {reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

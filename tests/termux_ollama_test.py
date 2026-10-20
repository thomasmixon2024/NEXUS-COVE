#!/usr/bin/env python3
"""Termux Ollama integration test for NEXUS COVE agent replies."""

import asyncio
import subprocess
import time
import sys
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "qwen2.5:0.5b"  # ~400 MB, fits in 4 GB RAM


async def check_ollama() -> bool:
    """Verify Ollama daemon is reachable."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
                return resp.status == 200
    except Exception:
        return False


async def pull_model() -> bool:
    """Pull model if not present."""
    proc = await asyncio.create_subprocess_exec(
        "ollama", "pull", MODEL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        print(f"  stderr: {stderr.decode().strip()}")
    return proc.returncode == 0


async def test_agent_reply() -> dict:
    """Test agent reply via Ollama Replier."""
    # Import after confirming environment
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from nexus_cove.agents.backends.ollama_replier import OllamaReplier, ModelUnavailable
    from nexus_cove.agents.backends.ollama_replier import default_system_prompt

    replier = OllamaReplier(MODEL, default_system_prompt("TestAgent"), OLLAMA_URL)
    start = time.monotonic()
    try:
        reply = await replier.areply("TestAgent says: hello from Termux")
        latency = time.monotonic() - start
        return {"ok": True, "reply": reply[:100], "latency_s": latency}
    except ModelUnavailable as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


async def main():
    print(f"[Termux Ollama Test] Target: {OLLAMA_URL}, Model: {MODEL}")

    # Check daemon
    if not await check_ollama():
        print("Starting ollama serve...")
        proc = subprocess.Popen(["ollama", "serve"])
        await asyncio.sleep(3)
        if not await check_ollama():
            print("❌ Ollama daemon failed to start")
            return 1

    # Pull model
    print(f"Pulling {MODEL}...")
    if not await pull_model():
        print("❌ Model pull failed")
        return 1

    # Test reply
    print("Testing agent reply...")
    result = await test_agent_reply()
    if result["ok"]:
        print(f"✅ PASS — latency: {result['latency_s']:.2f}s")
        print(f"   Reply: {result['reply']}")
        return 0
    else:
        print(f"❌ FAIL — {result['error']}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
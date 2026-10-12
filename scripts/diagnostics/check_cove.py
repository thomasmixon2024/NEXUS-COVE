import asyncio
import json

import websockets


async def main():
    async with websockets.connect("ws://127.0.0.1:8765") as ws:
        await ws.send(json.dumps({"version": 1, "action": "register", "username": "Alice"}))
        for _ in range(3):
            msg = json.loads(await asyncio.wait_for(ws.recv(), 3))
            print(msg)


asyncio.run(main())

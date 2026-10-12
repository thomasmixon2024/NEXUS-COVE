import websockets
from websockets.exceptions import InvalidStatus

from nexus_cove.transport.websocket.server import ALLOWED_ORIGINS, CoveWebSocketServer


async def test_cross_origin_browser_handshake_is_rejected() -> None:
    server = CoveWebSocketServer("127.0.0.1", 0)
    async with websockets.serve(
        server.handler, "127.0.0.1", 0, origins=list(ALLOWED_ORIGINS)
    ) as ws_server:
        port = next(iter(ws_server.sockets)).getsockname()[1]
        try:
            async with websockets.connect(
                f"ws://127.0.0.1:{port}", origin="https://evil.example"
            ):
                raise AssertionError("cross-origin handshake was accepted")
        except InvalidStatus as exc:
            assert exc.response.status_code == 403

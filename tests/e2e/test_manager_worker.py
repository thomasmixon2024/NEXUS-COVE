import asyncio

import websockets

from nexus_cove.agents.backends.deterministic_backend import DeterministicTestBackend
from nexus_cove.agents.worker import Worker
from nexus_cove.core.models import Agent, AgentStatus, Task
from nexus_cove.orchestration.manager import Manager
from nexus_cove.transport.websocket.server import CoveWebSocketServer


def test_manager_worker_complete_real_workflow(tmp_path) -> None:
    async def scenario() -> None:
        server = CoveWebSocketServer(port=18766)
        server_instance = await websockets.serve(server.handler, "127.0.0.1", 18766)
        from nexus_cove.storage.sqlite import SQLiteStorage

        manager = Manager("ws://127.0.0.1:18766", SQLiteStorage(str(tmp_path / "e2e.db")))
        await manager.connect()
        manager_listener = asyncio.create_task(manager.listen())
        worker = Worker(
            Agent("Aegis-Worker", frozenset({"general"}), AgentStatus.OFFLINE),
            DeterministicTestBackend(),
            "ws://127.0.0.1:18766",
        )
        worker_task = asyncio.create_task(worker.run())
        try:
            await asyncio.wait_for(manager._ready.wait(), timeout=2)
            task_id = await manager.submit(Task(prompt="real workflow"))
            for _ in range(40):
                if manager.metrics.tasks_completed == 1:
                    break
                await asyncio.sleep(0.025)
            assert manager.metrics.tasks_completed == 1
            assert manager.metrics.tasks_failed == 0
            assert manager.tasks.assignment(task_id) == "Aegis-Worker"
            assert manager.storage.summary()["success_rate"] == 1.0
            assert manager.storage.recent_results(1)[0]["task_id"] == task_id
        finally:
            worker_task.cancel()
            manager_listener.cancel()
            await asyncio.gather(worker_task, manager_listener, return_exceptions=True)
            await manager.close()
            server_instance.close()
            await server_instance.wait_closed()

    asyncio.run(scenario())

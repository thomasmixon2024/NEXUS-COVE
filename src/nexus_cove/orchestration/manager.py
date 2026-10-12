from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime
from typing import Any

from nexus_cove.agents.pause import is_paused
from nexus_cove.core.dialogue import DialogueGuard
from nexus_cove.core.models import Agent, AgentStatus, Task, TaskResult, TaskStatus
from nexus_cove.core.protocols import decode_message, encode_message, task_to_payload
from nexus_cove.observability.metrics import RuntimeMetrics
from nexus_cove.orchestration.registry import AgentRegistry
from nexus_cove.orchestration.scheduler import CapabilityLoadScheduler
from nexus_cove.orchestration.task_registry import TaskRegistry
from nexus_cove.utils.reconnection import ExponentialBackoff

log = logging.getLogger("nexus_cove.manager")


class Manager:
    def __init__(self, uri: str = "ws://127.0.0.1:8765", storage=None) -> None:
        if storage is None:
            raise ValueError("Manager requires a Storage instance")
        self.uri = uri
        self.storage = storage
        self.registry = AgentRegistry()
        self.tasks = TaskRegistry()
        self.scheduler = CapabilityLoadScheduler()
        self.metrics = RuntimeMetrics()
        self.websocket: Any = None
        self.identity = "Nexus-Manager"
        self._ready = asyncio.Event()
        self._dialogue = DialogueGuard()
        self._stopping = False
        self._reconnect_backoff = ExponentialBackoff()

    async def connect(self) -> None:
        import websockets

        self.storage.initialize()
        self.websocket = await websockets.connect(self.uri)
        await self.websocket.send(
            encode_message("register", agent_id=self.identity, capabilities=[])
        )
        log.info("manager connected", extra={"event": "manager_connected"})
        self._reconnect_backoff.reset()

    async def register_agent(self, data: dict[str, Any]) -> None:
        agent = Agent(
            agent_id=data["agent_id"],
            capabilities=frozenset(data.get("capabilities", [])),
            status=AgentStatus.IDLE,
        )
        self.registry.register(agent)
        self._ready.set()
        log.info(
            "agent registered", extra={"agent_id": agent.agent_id, "event": "agent_registered"}
        )

    async def submit(self, task: Task) -> str:
        if self.websocket is None:
            raise RuntimeError("Manager is not connected")
        self.tasks.add(task)
        self.tasks.set_status(task.task_id, TaskStatus.QUEUED)
        self.storage.record_task(task, TaskStatus.QUEUED.value)
        self.metrics.record_submission()
        agent = self.scheduler.select(task, self.registry.all())
        agent.current_load += 1
        agent.status = AgentStatus.BUSY
        self.tasks.assign(task.task_id, agent.agent_id)
        self.storage.update_task_status(task.task_id, TaskStatus.ASSIGNED.value)
        await self.websocket.send(
            encode_message("task_assign", recipient=agent.agent_id, task=task_to_payload(task))
        )
        log.info(
            "task assigned",
            extra={"task_id": task.task_id, "agent_id": agent.agent_id, "event": "task_assigned"},
        )
        return task.task_id

    async def handle_result(self, payload: dict[str, Any]) -> TaskResult:
        raw = payload.get("result")
        if not isinstance(raw, dict):
            raise ValueError("task_result payload missing 'result' object")
        try:
            measured = raw.get("measured_duration_seconds")
            result = TaskResult(
                task_id=raw["task_id"],
                agent_id=raw["agent_id"],
                status=TaskStatus(raw["status"]),
                started_at=datetime.fromisoformat(raw["started_at"]),
                finished_at=datetime.fromisoformat(raw["finished_at"]),
                output=raw.get("output"),
                error=raw.get("error"),
                metadata=raw.get("metadata") or {},
                measured_duration_seconds=(float(measured) if measured is not None else None),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid task_result payload: {exc}") from exc

        agent = self.registry.get(result.agent_id)
        if agent:
            agent.current_load = max(0, agent.current_load - 1)
            agent.status = AgentStatus.IDLE
        if self.tasks.get_optional(result.task_id) is None:
            log.warning(
                "result for unknown task_id=%s",
                result.task_id,
                extra={"event": "unknown_task_result"},
            )
        else:
            self.tasks.set_status(result.task_id, result.status)
        self.storage.record_result(result)
        self.metrics.record_result(result.duration_seconds, result.status == TaskStatus.COMPLETED)
        log.info(
            "task result recorded",
            extra={
                "task_id": result.task_id,
                "agent_id": result.agent_id,
                "event": f"task_{result.status.value}",
            },
        )
        return result

    async def _on_direct_message(self, message: dict) -> None:
        sender = message.get("sender", "Unknown")
        msg_content = message.get("message", "")
        recipient = message.get("recipient", self.identity)
        log.info(
            f"Received direct message from {sender} for {recipient}: {msg_content}",
            extra={"event": "direct_message_received"},
        )
        if recipient != self.identity or is_paused():
            return
        if not self._dialogue.should_reply(sender, message.get("sender_kind", "")):
            log.info(
                f"Not replying to {sender}: turn limit reached or unknown sender",
                extra={"event": "direct_message_suppressed"},
            )
            return
        response = f"Manager received: {msg_content}"
        await self.websocket.send(
            encode_message(
                "direct_message",
                sender=self.identity,
                recipient=sender,
                message=response,
            )
        )
        log.info(
            f"Sent automated response to {sender}",
            extra={"event": "automated_response_sent"},
        )

    async def listen(self) -> None:
        async for raw in self.websocket:
            try:
                message = decode_message(raw)
            except ValueError as exc:
                log.warning(
                    "ignoring invalid message: %s",
                    exc,
                    extra={"event": "invalid_message"},
                )
                continue
            action = message.get("action")
            if action == "agent_register":
                await self.register_agent(message)
            elif action == "task_result":
                try:
                    await self.handle_result(message)
                except ValueError as exc:
                    log.warning(
                        "ignoring invalid task_result: %s",
                        exc,
                        extra={"event": "task_result_invalid"},
                    )
            elif action == "direct_message":
                await self._on_direct_message(message)
            elif action == "control" and message.get("command") == "stop":
                log.info("Stop command received", extra={"event": "stop_received"})
                self._stopping = True
                return

    async def wait_for_agent(self, timeout: float = 10.0) -> None:
        await asyncio.wait_for(self._ready.wait(), timeout=timeout)

    async def close(self) -> None:
        if self.websocket is not None:
            await self.websocket.close()
        self.storage.close()

    async def run(self) -> None:
        while True:
            if self._stopping:
                return
            try:
                await self.connect()
                try:
                    await self.listen()
                except Exception as e:
                    # Unexpected error, log and break to reconnect
                    log.error(
                        "Unexpected error in WebSocket listener",
                        extra={"event": "listener_error", "error": str(e)},
                    )
            except Exception as e:
                # Connection failed, log and prepare to reconnect
                log.error(
                    "Failed to establish WebSocket connection",
                    extra={"event": "connection_failed", "error": str(e)},
                )

            if self._stopping:
                return

            # Reconnection logic with exponential backoff
            log.info(
                f"Attempting to reconnect in {self._reconnect_backoff.current_delay:.1f}s",
                extra={
                    "event": "reconnect_scheduled",
                    "delay": self._reconnect_backoff.current_delay,
                },
            )
            await self._reconnect_backoff.delay()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="ws://127.0.0.1:8765")
    parser.add_argument("--db", default="data/cove.db")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from nexus_cove.storage.sqlite import SQLiteStorage

    asyncio.run(Manager(args.uri, SQLiteStorage(args.db)).run())


if __name__ == "__main__":
    main()

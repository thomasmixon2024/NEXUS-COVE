from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path

from nexus_cove.agents.backends.base import AgentBackend
from nexus_cove.agents.backends.deterministic_backend import DeterministicTestBackend
from nexus_cove.agents.backends.ollama_replier import (
    ModelUnavailable,
    OllamaReplier,
    default_system_prompt,
)
from nexus_cove.agents.knowledge import (
    MAX_ITEM_CHARS,
    MAX_ITEMS_IN_PROMPT,
    KnowledgeStore,
    knowledge_folder,
    parse_shares,
)
from nexus_cove.agents.memory import AgentMemory
from nexus_cove.agents.pause import data_dir, is_agent_paused, set_agent_paused
from nexus_cove.agents.personality import (
    Personality,
    build_system_prompt,
    bundled_personality,
    load_personality,
)
from nexus_cove.agents.starter import ConversationStarter
from nexus_cove.agents.tools import toolkit_for
from nexus_cove.core.dialogue import DialogueGuard
from nexus_cove.core.models import Agent, AgentStatus, Task, TaskResult, TaskStatus
from nexus_cove.core.protocols import decode_message, encode_message
from nexus_cove.utils.reconnection import ExponentialBackoff

log = logging.getLogger("nexus_cove.worker")


class Worker:
    def __init__(
        self,
        agent: Agent,
        backend: AgentBackend,
        uri: str = "ws://127.0.0.1:8765",
        replier: OllamaReplier | None = None,
        starter: ConversationStarter | None = None,
        memory: AgentMemory | None = None,
        tools: tuple = (),
        knowledge: KnowledgeStore | None = None,
    ) -> None:
        self.agent = agent
        self.backend = backend
        self.uri = uri
        self._replier = replier
        self._starter = starter
        self._memory = memory
        self._tools = tools
        self._knowledge = knowledge
        self._inflight: set[asyncio.Task] = set()
        self._stopping = False
        self._reconnect_backoff = ExponentialBackoff()
        self._dialogue = DialogueGuard()

    async def _send_presence(self, ws) -> None:
        await ws.send(encode_message("presence", paused=is_agent_paused(self.agent.agent_id)))

    async def _announce(self, ws, text: str) -> None:
        await ws.send(
            encode_message("broadcast", sender=self.agent.agent_id, message=text, kind="system")
        )

    async def _group_reply(self, sender: str, msg_content: str) -> str | None:
        if self._replier is None:
            return f"{self.agent.agent_id} heard you, {sender}."
        try:
            reply = await self._replier.areply(
                self._build_prompt(sender, msg_content, "to the whole group")
            )
            visible, _ = parse_shares(reply)  # group replies never carry shared items
            return visible or None
        except ModelUnavailable as exc:
            log.error(
                "Language model unavailable for group reply",
                extra={"event": "model_unavailable", "error": str(exc)},
            )
            return None

    def _record(self, direction: str, peer: str, text: str) -> None:
        if self._memory is not None:
            self._memory.append(direction, peer, text)

    def _build_prompt(self, sender: str, text: str, note: str) -> str:
        """Recent memory, then tool results, then the message itself."""
        parts: list[str] = []
        if self._memory is not None:
            # The current message is already in memory; leave it out of the memory block.
            recent = [
                entry
                for entry in self._memory.recent(8)
                if not (entry["direction"] == "received" and entry["text"] == text)
            ][-6:]
            if recent:
                lines = [
                    f"- {'said' if entry['direction'] == 'sent' else 'heard'} "
                    f"({entry['peer']}): {entry['text']}"
                    for entry in recent
                ]
                parts.append("Recent memory:\n" + "\n".join(lines))
        if self._knowledge is not None:
            items = list(self._knowledge.items().items())[:MAX_ITEMS_IN_PROMPT]
            if items:
                blocks = [f"## {title}\n{body[:MAX_ITEM_CHARS]}" for title, body in items]
                parts.append(
                    "Your own knowledge (only you hold this):\n\n"
                    + "\n\n".join(blocks)
                    + "\n\nSharing is your choice. To share one item with the agent you are "
                    "talking to, write a line SHARE: <title> in your reply. "
                    "Otherwise write nothing."
                )
        for tool in self._tools:
            result = tool.run(text)
            if result:
                parts.append(result)
        target = f" {note}" if note else ""
        parts.append(f"{sender} says{target}: {text}")
        return "\n\n".join(parts)

    async def _share_item(self, ws, peer: str, title: str) -> None:
        content = self._knowledge.find(title) if self._knowledge is not None else None
        if content is None:
            log.info(
                f"Named an item it does not hold, not shared: {title}",
                extra={"event": "share_skipped"},
            )
            return
        body = f"[shared knowledge: {title}]\n{content[:MAX_ITEM_CHARS]}"
        await ws.send(
            encode_message(
                "direct_message", sender=self.agent.agent_id, recipient=peer, message=body
            )
        )
        self._record("sent", peer, body)
        log.info(
            f"Shared knowledge item with {peer}",
            extra={"event": "knowledge_shared", "item": title, "peer": peer},
        )

    def _spawn(self, coro) -> None:
        task = asyncio.create_task(coro)
        self._inflight.add(task)
        task.add_done_callback(self._task_finished)

    def _task_finished(self, task: asyncio.Task) -> None:
        self._inflight.discard(task)
        if not task.cancelled() and task.exception() is not None:
            log.error(
                "Reply task failed",
                extra={"event": "reply_failed", "error": str(task.exception())},
            )

    def _cancel_inflight(self) -> None:
        for task in list(self._inflight):
            task.cancel()

    async def _execute_assigned_task(self, ws, message: dict) -> None:
        """Execute a task_assign payload off the listener so control stays responsive."""
        task_data = message.get("task")
        if not isinstance(task_data, dict):
            log.error("task_assign missing task payload", extra={"event": "task_assign_invalid"})
            return
        try:
            task = Task(
                task_id=task_data["task_id"],
                prompt=task_data["prompt"],
                task_type=task_data.get("task_type", "general"),
                required_capabilities=frozenset(task_data.get("required_capabilities", [])),
                priority=int(task_data.get("priority", 0)),
                parent_task_id=task_data.get("parent_task_id"),
                created_at=datetime.fromisoformat(task_data["created_at"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            log.error(
                "task_assign payload invalid: %s",
                exc,
                extra={"event": "task_assign_invalid"},
            )
            return

        self.agent.status = AgentStatus.BUSY
        try:
            result = await self.backend.execute(task, self.agent.agent_id)
        except Exception as exc:
            now = datetime.now(UTC)
            result = TaskResult(
                task_id=task.task_id,
                agent_id=self.agent.agent_id,
                status=TaskStatus.FAILED,
                started_at=now,
                finished_at=now,
                error=str(exc),
            )
            log.exception(
                "task failed",
                extra={
                    "task_id": task.task_id,
                    "agent_id": self.agent.agent_id,
                    "event": "task_failed",
                },
            )
        else:
            log.info(
                "task completed",
                extra={
                    "task_id": task.task_id,
                    "agent_id": self.agent.agent_id,
                    "event": "task_completed",
                },
            )
        finally:
            self.agent.status = AgentStatus.IDLE

        if self._stopping:
            return
        try:
            await ws.send(encode_message("task_result", result=result))
        except Exception as exc:
            log.warning(
                "failed to send task_result: %s",
                exc,
                extra={"event": "task_result_send_failed", "task_id": task.task_id},
            )

    async def _answer_direct(self, ws, sender: str, msg_content: str) -> None:
        if self._replier is None:
            reply_text = (
                f"Hello {sender}! I am {self.agent.agent_id}, "
                f"a NEXUS COVE worker agent. "
                f"I received your message: '{msg_content}'"
            )
        else:
            try:
                reply_text = await self._replier.areply(self._build_prompt(sender, msg_content, ""))
            except ModelUnavailable as exc:
                log.error(
                    "Language model unavailable",
                    extra={"event": "model_unavailable", "error": str(exc)},
                )
                reply_text = "My language model is unavailable right now."
        reply_text, shared_titles = parse_shares(reply_text)
        # Re-check: a pause may have arrived while the reply was being written.
        if is_agent_paused(self.agent.agent_id):
            log.info(
                f"Paused: reply to {sender} dropped",
                extra={"event": "paused_reply_dropped"},
            )
            return
        await ws.send(
            encode_message(
                "direct_message",
                sender=self.agent.agent_id,
                recipient=sender,
                message=reply_text,
            )
        )
        self._record("sent", sender, reply_text)
        for title in shared_titles:
            await self._share_item(ws, sender, title)
        log.info(
            f"Sent automated response to {sender}",
            extra={"event": "automated_response_sent"},
        )

    async def _answer_group(self, ws, sender: str, msg_content: str) -> None:
        group_text = await self._group_reply(sender, msg_content)
        if not group_text or is_agent_paused(self.agent.agent_id):
            return
        await ws.send(encode_message("broadcast", sender=self.agent.agent_id, message=group_text))
        self._record("sent", sender, group_text)
        log.info("Sent group reply", extra={"event": "group_reply_sent"})

    async def _send_direct(self, ws, text: str) -> None:
        assert self._starter is not None
        await ws.send(
            encode_message(
                "direct_message",
                sender=self.agent.agent_id,
                recipient=self._starter.peer,
                message=text,
            )
        )

    async def _on_direct_message(self, ws, message: dict) -> None:
        sender = message.get("sender", "Unknown")
        msg_content = message.get("message", "")
        log.info(
            f"Received direct message from {sender}: {msg_content}",
            extra={"event": "direct_message_received"},
        )
        if is_agent_paused(self.agent.agent_id):
            log.info(
                f"Paused: not replying to {sender}",
                extra={"event": "paused_no_reply"},
            )
            return
        if not self._dialogue.should_reply(sender, message.get("sender_kind", "")):
            log.info(
                f"Not replying to {sender}: turn limit reached or unknown sender",
                extra={"event": "direct_message_suppressed"},
            )
            return
        self._record("received", sender, msg_content)
        self._spawn(self._answer_direct(ws, sender, msg_content))

    async def _on_broadcast(self, ws, message: dict) -> None:
        sender = message.get("sender", "Unknown")
        msg_content = message.get("message", "")
        log.info(
            f"Received broadcast from {sender}: {msg_content}",
            extra={"event": "broadcast_received"},
        )
        if sender != self.agent.agent_id and message.get("kind") != "system":
            self._record("received", sender, msg_content)
        # Answer group messages from humans only.
        if (
            message.get("sender_kind") == "html_client"
            and not sender.startswith("user_")
            and not is_agent_paused(self.agent.agent_id)
        ):
            self._spawn(self._answer_group(ws, sender, msg_content))

    async def _on_control(self, ws, message: dict) -> bool:
        """Apply control command. Returns True if the worker should stop."""
        if message.get("sender_kind") != "html_client":
            return False
        command = message.get("command")
        name = self.agent.agent_id
        if command == "pause":
            await self._announce(ws, f"{name} is paused. It will not reply until it is resumed.")
            set_agent_paused(name, True)
            self._cancel_inflight()
            await self._send_presence(ws)
        elif command == "resume":
            set_agent_paused(name, False)
            await self._announce(ws, f"{name} is active again.")
            await self._send_presence(ws)
        elif command == "stop":
            self._stopping = True
            self._cancel_inflight()
        log.info(
            f"Control command applied: {command}",
            extra={"event": "control_applied", "command": command},
        )
        return self._stopping

    async def _dispatch(self, ws, message: dict) -> bool:
        """Route one protocol message. Returns True if the session should end."""
        action = message.get("action")
        if action == "task_assign":
            self._spawn(self._execute_assigned_task(ws, message))
        elif action == "direct_message":
            await self._on_direct_message(ws, message)
        elif action == "broadcast":
            await self._on_broadcast(ws, message)
        elif action == "control":
            return await self._on_control(ws, message)
        return False

    async def run(self) -> None:
        import websockets

        while True:
            ws = None
            starter_task = None
            try:
                ws = await websockets.connect(self.uri)
                await ws.send(
                    encode_message(
                        "register",
                        agent_id=self.agent.agent_id,
                        capabilities=sorted(self.agent.capabilities),
                    )
                )

                await self._send_presence(ws)

                # Reset reconnect delay on successful connection
                self._reconnect_backoff.reset()

                if self._starter is not None:
                    starter_task = asyncio.create_task(
                        self._starter.run(lambda text, _ws=ws: self._send_direct(_ws, text))
                    )

                async for raw in ws:
                    try:
                        message = decode_message(raw)
                    except ValueError as exc:
                        log.warning(
                            "ignoring invalid message: %s",
                            exc,
                            extra={"event": "invalid_message"},
                        )
                        continue
                    if await self._dispatch(ws, message):
                        break

            except websockets.exceptions.ConnectionClosed:
                # Connection was closed, attempt to reconnect
                log.info(
                    "WebSocket connection closed, attempting reconnection",
                    extra={"event": "connection_closed"},
                )

            except Exception as e:
                # Unexpected error, log and attempt to reconnect
                log.error(
                    "Unexpected error in WebSocket worker",
                    extra={"event": "worker_error", "error": str(e)},
                )

            finally:
                if starter_task is not None:
                    starter_task.cancel()
                # Ensure websocket is closed if it was opened
                if ws is not None:
                    try:
                        await ws.close()
                    except Exception as exc:  # close errors must not mask the original failure
                        log.warning(
                            "websocket close failed",
                            extra={"event": "close_failed", "error": str(exc)},
                        )

            if self._stopping:
                log.info("Stopped by network stop command", extra={"event": "stopped"})
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


def resolve_personality(value: str | None, agent_name: str) -> Personality | None:
    if value:
        path = Path(value)
        if not path.is_file():
            found = bundled_personality(value)
            if found is None:
                raise SystemExit(f"No personality file found for {value!r}.")
            path = found
        return load_personality(path)
    found = bundled_personality(agent_name)
    return load_personality(found) if found is not None else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Aegis-Worker")
    parser.add_argument("--capability", action="append", default=None)
    parser.add_argument(
        "--test-backend",
        action="store_true",
        help="Use the deterministic backend; intended for development/tests only",
    )
    parser.add_argument("--uri", default="ws://127.0.0.1:8765")
    parser.add_argument(
        "--model",
        default=None,
        help="Ollama model for direct-message replies, e.g. qwen2.5:0.5b. Omit for fixed replies.",
    )
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--ollama-timeout", type=float, default=300.0,
        help="Ollama request timeout in seconds (default: 300)"
    )
    parser.add_argument(
        "--personality",
        default=None,
        help="Personality name or .toml path. Default: the bundled file for --name.",
    )
    parser.add_argument(
        "--start-conversation",
        default=None,
        metavar="PEER",
        help="Periodically send a question to this peer agent.",
    )
    parser.add_argument(
        "--start-interval", type=float, default=300.0, help="Seconds between starter messages."
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    capabilities = frozenset(args.capability or ["general"])
    if not args.test_backend:
        raise SystemExit(
            "No production execution backend is configured. "
            "Use --test-backend only for local development/tests."
        )
    agent = Agent(args.name, capabilities, AgentStatus.OFFLINE)
    personality = resolve_personality(args.personality, args.name)
    if args.start_conversation and personality is None:
        raise SystemExit("--start-conversation needs a personality; none found for this agent.")
    system_prompt = (
        build_system_prompt(personality) if personality else default_system_prompt(args.name)
    )
    replier = (
        OllamaReplier(args.model, system_prompt, base_url=args.ollama_url, timeout=args.ollama_timeout)
        if args.model else None
    )
    starter = (
        ConversationStarter(
            peer=args.start_conversation,
            personality=personality,
            interval=args.start_interval,
            replier=replier,
            paused=lambda: is_agent_paused(args.name),
        )
        if args.start_conversation
        else None
    )
    memory = AgentMemory(data_dir() / "memory" / f"{args.name}.jsonl")
    tools = toolkit_for(args.name, memory)
    knowledge = KnowledgeStore(knowledge_folder(args.name))
    asyncio.run(
        Worker(
            agent,
            DeterministicTestBackend(),
            args.uri,
            replier,
            starter,
            memory=memory,
            tools=tools,
            knowledge=knowledge,
        ).run()
    )


if __name__ == "__main__":
    main()

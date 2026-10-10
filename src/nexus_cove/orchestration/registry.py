from __future__ import annotations

from nexus_cove.core.models import Agent, AgentStatus


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}

    def register(self, agent: Agent) -> None:
        self._agents[agent.agent_id] = agent

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    def available(self) -> list[Agent]:
        return [
            a for a in self._agents.values() if a.status in {AgentStatus.IDLE, AgentStatus.BUSY}
        ]

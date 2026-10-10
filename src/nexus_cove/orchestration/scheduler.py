from __future__ import annotations

from nexus_cove.core.exceptions import AgentUnavailable
from nexus_cove.core.models import Agent, AgentStatus, Task


class CapabilityLoadScheduler:
    """Select the least-loaded healthy agent satisfying task capabilities."""

    def select(self, task: Task, agents: list[Agent]) -> Agent:
        candidates = [
            agent
            for agent in agents
            if agent.status in {AgentStatus.IDLE, AgentStatus.BUSY}
            and task.required_capabilities.issubset(agent.capabilities)
        ]
        if not candidates:
            raise AgentUnavailable(
                f"No available agent satisfies capabilities={sorted(task.required_capabilities)}"
            )
        return min(candidates, key=lambda agent: (agent.current_load, agent.agent_id))

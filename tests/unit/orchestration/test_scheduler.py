import pytest

from nexus_cove.core.exceptions import AgentUnavailable
from nexus_cove.core.models import Agent, AgentStatus, Task
from nexus_cove.orchestration.scheduler import CapabilityLoadScheduler


def test_scheduler_prefers_capable_least_loaded_agent() -> None:
    task = Task(prompt="code", required_capabilities=frozenset({"python"}))
    agents = [
        Agent("zeta", frozenset({"python"}), AgentStatus.IDLE, current_load=0),
        Agent("alpha", frozenset({"python"}), AgentStatus.BUSY, current_load=1),
    ]
    assert CapabilityLoadScheduler().select(task, agents).agent_id == "zeta"


def test_scheduler_rejects_missing_capability() -> None:
    task = Task(prompt="code", required_capabilities=frozenset({"python"}))
    agents = [Agent("a", frozenset({"general"}), AgentStatus.IDLE)]
    with pytest.raises(AgentUnavailable):
        CapabilityLoadScheduler().select(task, agents)

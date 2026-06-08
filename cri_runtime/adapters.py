"""Agent adapter framework for external workloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class AgentAction:
    agent_type: str
    action_type: str
    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class AgentAdapter(Protocol):
    agent_type: str

    def normalize(self, request: dict[str, Any]) -> AgentAction:
        ...


@dataclass
class GenericAdapter:
    agent_type: str = "generic"

    def normalize(self, request: dict[str, Any]) -> AgentAction:
        return AgentAction(
            agent_type=self.agent_type,
            action_type=str(request.get("action_type", request.get("type", "unknown"))),
            payload=dict(request.get("payload", request)),
            metadata=dict(request.get("metadata", {})),
        )


class LangGraphAdapter(GenericAdapter):
    agent_type = "langgraph"


class OpenAIAgentsAdapter(GenericAdapter):
    agent_type = "openai_agents"


class AutoGenAdapter(GenericAdapter):
    agent_type = "autogen"


class OpenHandsAdapter(GenericAdapter):
    agent_type = "openhands"


class CrewAIAdapter(GenericAdapter):
    agent_type = "crewai"


@dataclass
class AdapterRegistry:
    adapters: dict[str, AgentAdapter] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for adapter in (
            GenericAdapter(),
            LangGraphAdapter(),
            OpenAIAgentsAdapter(),
            AutoGenAdapter(),
            OpenHandsAdapter(),
            CrewAIAdapter(),
        ):
            self.register(adapter)

    def register(self, adapter: AgentAdapter) -> None:
        self.adapters[adapter.agent_type] = adapter

    def normalize(self, agent_type: str, request: dict[str, Any]) -> AgentAction:
        adapter = self.adapters.get(agent_type, self.adapters["generic"])
        return adapter.normalize(request)


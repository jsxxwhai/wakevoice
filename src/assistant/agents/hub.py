"""Multi-agent framework: named agents with roles, routed by intent.

Each agent is a lightweight object with a role prompt and an optional LLM
call. Agents run concurrently via a thread pool for parallel tool use.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class Agent:
    name: str
    role: str
    description: str = ""
    system_prompt: str = ""
    handler: Callable[[str, AgentContext], str] | None = None


@dataclass
class AgentContext:
    config: Any = None
    skills: Any = None
    speak: Callable[[str, str | None], Any] | None = None
    extras: dict[str, Any] = field(default_factory=dict)


    def to_skill_context(self):
        """Convert to a SkillContext for skill execution."""
        from ..skills.base import SkillContext
        return SkillContext(config=self.config, speak=self.speak)


class AgentHub:
    """Registry and dispatcher for agents."""

    def __init__(self, max_workers: int = 4):
        self._agents: dict[str, Agent] = {}
        self._max_workers = max_workers
        self._pool = None

    def _get_pool(self):
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=self._max_workers)
        return self._pool

    def register(self, agent: Agent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def names(self) -> list[str]:
        return list(self._agents)

    def dispatch(self, name: str, text: str, ctx: AgentContext) -> str:
        agent = self._agents.get(name)
        if agent is None:
            return f"未知 agent: {name}"
        if agent.handler:
            return agent.handler(text, ctx)
        return f"agent {name} 已收到：{text}"

    def dispatch_async(self, name: str, text: str, ctx: AgentContext) -> Any:
        return self._get_pool().submit(self.dispatch, name, text, ctx)

    def shutdown(self) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=False)
            self._pool = None

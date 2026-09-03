"""LLM-powered agent that routes skills and generates emotional replies."""
from __future__ import annotations

import logging

from ..core.llm import LLMClient
from .hub import AgentContext

log = logging.getLogger(__name__)


class LLMAgent:
    """Agent that uses an LLM to (1) decide intent, (2) call a skill, (3) reply warmly.

    When the underlying LLM exposes `respond_with_tools`, the agent runs a
    multi-turn tool-calling loop so the model can chain several skills before
    producing a final emotional answer. Otherwise it falls back to the single-
    shot `respond_with_emotion` path.
    """

    def __init__(self, name: str = "general", llm: LLMClient | None = None, memory=None,
                 max_tool_turns: int = 4):
        self.name = name
        self.llm = llm
        self.memory = memory
        self.max_tool_turns = max_tool_turns

    def _skill_manifests(self, ctx: AgentContext) -> list[dict]:
        if not ctx or not ctx.skills:
            return []
        return ctx.skills.all_manifests()

    def _skills_desc(self, ctx: AgentContext) -> str:
        return "\n".join(
            f"- {m['name']}: {m['description']}" for m in self._skill_manifests(ctx)
        )

    def _execute_skill(self, ctx: AgentContext):
        """Return a callable (name, args) -> str that runs a skill by name."""
        def run(name: str, args: str = ""):
            if not ctx or not ctx.skills:
                return "没有可用的技能。"
            skill = ctx.skills.find(name)
            if skill is None:
                return "未知技能：" + str(name)
            if isinstance(args, dict):
                params = dict(args)
                params.setdefault("text", "")
            else:
                params = {"text": str(args) if args is not None else ""}
            try:
                return skill.run(params, ctx.to_skill_context())
            except Exception as e:
                log.exception("skill %s failed", name)
                return "技能执行失败：" + str(e)
        return run

    def respond(self, text: str, ctx: AgentContext) -> tuple[str, str]:
        """Return (reply, emotion)."""
        # 1) try local skill first (fast, offline)
        if ctx and ctx.skills:
            hit = ctx.skills.route(text)
            if hit:
                skill, params = hit
                try:
                    result = skill.run(params, ctx.to_skill_context())
                    if self.memory is not None:
                        self.memory.add("user", text)
                        self.memory.add("assistant", result)
                    return result, "neutral"
                except Exception:
                    log.exception("skill %s failed", skill.name)

        # 2) fallback to LLM
        if self.llm:
            try:
                history = self.memory.to_messages() if self.memory else None
                if hasattr(self.llm, "respond_with_tools"):
                    tools = self._skill_manifests(ctx)
                    reply, emotion = self.llm.respond_with_tools(
                        text, tools=tools, execute_tool=self._execute_skill(ctx),
                        max_turns=self.max_tool_turns, history=history,
                    )
                else:
                    desc = self._skills_desc(ctx)
                    reply, emotion = self.llm.respond_with_emotion(
                        text, skills_desc=desc, history=history,
                    )
                if self.memory is not None:
                    self.memory.add("user", text)
                    self.memory.add("assistant", reply)
                return reply, emotion
            except Exception as e:
                log.warning("LLM unavailable: %s", e)

        return f"我收到你说的：{text}", "neutral"

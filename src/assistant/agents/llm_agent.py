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

        # 3) fully offline / unmatched: answer honestly and helpfully instead of
        #    mechanically echoing the input back ("我收到你说的：…").
        t = (text or "").strip()
        if not t:
            return "我在这儿，你说吧。", "neutral"
        low = t.lower()
        if any(k in low for k in ("你好", "您好", "hi", "hello", "嗨", "哈喽")):
            return "你好呀！我能帮你打开软件、查时间、记东西，直接说就好。", "happy"
        if any(k in low for k in ("谢谢", "感谢", "3q", "thank")):
            return "不客气，随时叫我～", "happy"
        if any(k in low for k in ("再见", "拜拜", "晚安", "bye")):
            return "再见，有需要随时叫我！", "neutral"
        if len(t) <= 4 and t.endswith("吗"):
            return "可以的，你说的“" + t + "”我记住了。不过现在没联网也能做的，我能帮你开软件、报时间、复制粘贴、截图这些，试试看？", "neutral"
        return "这句话我还不会，可以换个说法试试，比如“打开记事本”“现在几点”“复制这段话”。要是连了网，我也能陪你聊得更顺。", "neutral"

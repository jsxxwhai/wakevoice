"""Tests for LLM agent emotion routing (uses a fake LLM, no network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.agents.hub import AgentContext
from assistant.agents.llm_agent import LLMAgent
from assistant.skills import apps as A
from assistant.skills import control as C
from assistant.skills.base import SkillRegistry


class FakeLLM:
    def respond_with_emotion(self, text, skills_desc="", history=None):
        return ("今天真开心呀！", "happy")


def _ctx():
    reg = SkillRegistry()
    reg.register(A.open_app_skill())
    C.register_control_skills(reg)
    return AgentContext(config=None, skills=reg, speak=None)


def test_skill_priority_over_llm(monkeypatch):
    # Avoid a real pyautogui.write() side effect (flaky fail-safe on mouse pos).
    monkeypatch.setattr(C, "_type_text", lambda text: "已输入 " + str(len(text)) + " 个字符")
    agent = LLMAgent(name="general", llm=FakeLLM())
    reply, emotion = agent.respond("输入你好", _ctx())
    assert "已输入" in reply
    assert emotion == "neutral"


def test_respond_with_emotion_handles_fenced_json():
    """respond_with_emotion must parse triple-backtick fenced JSON."""
    from assistant.core.llm import LLMClient

    class Fenced(LLMClient):
        def chat(self, messages, json_mode=False):
            return '```json\n{"reply": "你好呀", "emotion": "happy"}\n```'

    reply, emotion = Fenced().respond_with_emotion("hi")
    assert reply == "你好呀"
    assert emotion == "happy"


def test_llm_fallback_emotion():
    agent = LLMAgent(name="general", llm=FakeLLM())
    reply, emotion = agent.respond("讲个笑话", _ctx())
    assert reply == "今天真开心呀！"
    assert emotion == "happy"

class ToolLLM:
    """Fake LLM that exercises the multi-turn tool-calling path."""
    def __init__(self):
        self.calls = []

    def respond_with_tools(self, text, tools=None, execute_tool=None,
                           max_turns=4, history=None):
        self.calls.append(text)
        # call one tool, then return a final answer
        if execute_tool is not None:
            result = execute_tool("type_text", "hello")
            self.calls.append(("tool_result", result))
        return ("ok", "happy")


def test_llm_uses_tool_loop_when_available():
    agent = LLMAgent(name="general", llm=ToolLLM())
    reply, emotion = agent.respond("abcdefg", _ctx())
    assert reply == "ok"
    assert emotion == "happy"
    assert agent.llm.calls[0] == "abcdefg"
    assert agent.llm.calls[1][0] == "tool_result"


def test_execute_skill_accepts_dict_args():
    """The tool-calling executor forwards dict args to the skill params."""
    agent = LLMAgent(name="general")
    ctx = _ctx()
    run = agent._execute_skill(ctx)

    # dict args map onto skill params
    skill = ctx.skills.find("type_text")
    assert skill is not None

    class _Rec:
        pass
    rec = _Rec()
    rec.level = None
    rec.text = None

    def fake_run(params, sctx):
        rec.level = params.get("level")
        rec.text = params.get("text")
        return "ok"

    skill.handler = fake_run
    assert run("type_text", {"level": "42"}) == "ok"
    assert rec.level == "42"
    assert rec.text == ""

    # string args fall back to the text param
    assert run("type_text", "hi") == "ok"
    assert rec.text == "hi"


def test_offline_fallback_natural_replies():
    """When no skill matches and no LLM is set, replies must be natural and
    helpful instead of mechanically echoing the user text back."""
    reg = SkillRegistry()
    agent = LLMAgent(name="general")  # no llm -> hits the final fallback
    ctx = AgentContext(config=None, skills=reg, speak=None)

    reply, emotion = agent.respond("你好呀", ctx)
    assert "你好呀" in reply
    assert emotion == "happy"

    reply, emotion = agent.respond("讲个笑话", ctx)
    assert "我收到你说的" not in reply
    assert "换个说法" in reply
    assert emotion == "neutral"

    reply, emotion = agent.respond("谢谢", ctx)
    assert "不客气" in reply
    assert emotion == "happy"

    reply, emotion = agent.respond("拜拜", ctx)
    assert "再见" in reply
    assert emotion == "neutral"

    reply, emotion = agent.respond("", ctx)
    assert "我在这儿" in reply
    assert emotion == "neutral"

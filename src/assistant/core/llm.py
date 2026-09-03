"""LLM integration: chat + emotion + intent routing.

Uses any Chat Completions-compatible endpoint (DeepSeek, Ollama, vLLM, etc.)
via `base_url` with a lightweight structured prompt so the model returns
JSON with `reply` and `emotion` fields, enabling emotional voice output.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

EMOTIONS = ["neutral", "happy", "sad", "angry", "fear", "excited", "gentle", "calm", "surprised"]


class LLMClient:
    """Thin wrapper over the optional LLM SDK; lazy import to keep memory low."""

    def __init__(self, base_url: str | None = None, api_key_env: str = "LLM_API_KEY",
                 model: str = "gpt-4o-mini", temperature: float = 0.7,
                 timeout: float = 20.0):
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self._client = None

    def _get_client(self):
        if self._client is None:
            import os

            from openai import OpenAI  # lazy import
            kwargs = {}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(api_key=os.environ.get(self.api_key_env, "sk-none"), **kwargs)
        return self._client

    def chat(self, messages: list[dict], json_mode: bool = False) -> str:
        client = self._get_client()
        kwargs = {"model": self.model, "messages": messages,
                  "temperature": self.temperature, "timeout": self.timeout}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def respond_with_emotion(self, user_text: str, system_prompt: str = "",
                             skills_desc: str = "", history: list | None = None) -> tuple[str, str]:
        """Return (reply, emotion) inferred from the user utterance."""
        sys_prompt = system_prompt or "你是一个友好的中文语音助手，回复要自然、有温度、口语化。"
        if skills_desc:
            sys_prompt += "\n你可以使用以下技能：\n" + skills_desc
        sys_prompt += (
            "\n请以 JSON 返回，格式：{\"reply\": \"你的回复\", \"emotion\": \"情绪\"}。"
            f"情绪必须是这些之一: {EMOTIONS}。"
        )
        messages = [{"role": "system", "content": sys_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        raw = self.chat(messages, json_mode=True)
        data = self._extract_json(raw)
        if not isinstance(data, dict):
            return raw, "neutral"
        reply = data.get("reply") or raw or ""
        emotion = data.get("emotion", "neutral")
        if emotion not in EMOTIONS:
            emotion = "neutral"
        return reply, emotion

    # ---- tool-calling (multi-turn) ----
    def _extract_json(self, raw: str):
        """Best-effort parse of a JSON object embedded in a reply (handles fences)."""
        import re as _re
        text = (raw or "").strip()
        # strip triple/backtick fences and optional 'json' language tag
        text = _re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = _re.sub(r"```\s*$", "", text).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = _re.search(r"\{.*\}", text, _re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    return None
        return None

    def respond_with_tools(self, user_text, tools, system_prompt="",
                           execute_tool=None, max_turns=4, history=None):
        """Multi-turn tool-calling loop.

        `tools` is a list of dicts with `name` and `description`.
        `execute_tool(name)` runs one skill and returns its string result.
        The model may call tools across several turns, then produce a final reply.
        Returns (reply, emotion). If the model never calls a tool, it just answers.
        """
        if execute_tool is None:
            def execute_tool(name, args=""):
                return ""

        tool_list = "\n".join(
            f"- {t['name']}: {t.get('description', '')}" for t in tools
        ) if tools else ""
        sys_prompt = system_prompt or "你是一个友好的中文语音助手，回复要自然、有温度、口语化。"
        if tool_list:
            sys_prompt += (
                "\n你可以按需调用以下技能，调用时先返回 JSON "
                '{"action": "call_tool", "tool": "<工具名>", "args": "<参数>"}；'
                "执行结果会回传给你。最终回答请返回 JSON "
                '{"reply": "你的回复", "emotion": "情绪"}。'
                f"情绪必须是这些之一: {EMOTIONS}。\n可用技能：\n" + tool_list
            )
        else:
            sys_prompt += (
                "\n请以 JSON 返回，格式：{\"reply\": \"你的回复\", \"emotion\": \"情绪\"}。"
                f"情绪必须是这些之一: {EMOTIONS}。"
            )

        messages = [{"role": "system", "content": sys_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_text})

        for _ in range(max(1, max_turns)):
            raw = self.chat(messages, json_mode=True)
            data = self._extract_json(raw)
            if not isinstance(data, dict):
                return raw, "neutral"
            if data.get("action") == "call_tool" and data.get("tool"):
                tool = data.get("tool")
                args = data.get("args", "")
                try:
                    result = execute_tool(tool, args)
                except Exception as e:
                    result = "调用失败：" + str(e)
                messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
                messages.append({"role": "user", "content": "工具结果：" + str(result)})
                continue
            reply = data.get("reply") or raw or ""
            emotion = data.get("emotion", "neutral")
            if emotion not in EMOTIONS:
                emotion = "neutral"
            return reply, emotion
        return "抱歉，我尝试了好几次都没能完成这个任务。", "neutral"

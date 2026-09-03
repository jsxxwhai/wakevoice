"""Bridge skill: call configured MCP server tools from natural language."""
from __future__ import annotations

import json
import re

from .base import Skill


def make_mcp_skill(mcp_manager) -> Skill:
    """Return a skill that routes `mcp <server> <tool> <args-json>` to a tool call."""

    def run(params, ctx):
        server = params.get("server", "")
        tool = params.get("tool", "")
        args_raw = params.get("args", "{}")
        try:
            args = json.loads(args_raw) if args_raw else {}
        except json.JSONDecodeError:
            args = {"input": args_raw}
        try:
            result = mcp_manager.call(server, tool, args)
            return json.dumps(result, ensure_ascii=False)[:2000]
        except Exception as e:
            return "调用 MCP 工具失败：" + str(e)

    return Skill(
        name="mcp_call",
        description="调用已配置的 MCP 服务器工具",
        patterns=[re.compile(r"(?:调用|使用)?(?:extension|mcp)\s+(?P<server>\S+)\s+(?P<tool>\S+)\s*(?P<args>\{.*\}|\S+)?")],
        keywords=["mcp"],
        handler=run,
    )

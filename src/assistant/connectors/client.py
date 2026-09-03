"""MCP (Model Context Protocol) client: connect to and call external MCP servers.

Users can configure arbitrary MCP servers in config under `extension.servers`
(see config/config.example.yaml).
Supports the stdio transport (spawn a subprocess) and the HTTP/SSE transport.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import threading
from typing import Any

from ..core.errors import MCPServerError

log = logging.getLogger(__name__)


class MCPServer:
    """A single MCP server connection (stdio or HTTP)."""

    def __init__(self, name: str, command: list[str] | None = None,
                 url: str | None = None, env: dict[str, str] | None = None,
                 transport: str = "http"):
        self.name = name
        self.command = command
        self.url = url
        self.env = env or {}
        self.transport = transport  # "http" | "streamable_http" | "stdio"
        self._session_id: str | None = None
        self._proc = None
        self._id = 0
        self._lock = threading.Lock()

    # ---- stdio transport ----
    def _spawn(self) -> subprocess.Popen:
        if not self.command:
            raise MCPServerError(f"MCP server '{self.name}' has no command/url")
        proc = subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            env={**os.environ, **self.env},
        )
        # initialize handshake
        self._send_stdio(proc, "initialize", {"protocolVersion": "2024-11-05"}, self._next_id())
        return proc

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _send_stdio(self, proc, method: str, params: dict, msg_id: int) -> Any:
        req = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()
        while True:
            line = proc.stdout.readline()
            if not line:
                raise MCPServerError(f"MCP server '{self.name}' closed stream")
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                # tolerate blank/keep-alive lines from noisy stdio servers
                continue
            if resp.get("id") == msg_id:
                if "error" in resp:
                    raise MCPServerError(str(resp["error"]))
                return resp.get("result", {})

    def _rpc_stdio(self, method: str, params: dict) -> Any:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._proc = self._spawn()
            return self._send_stdio(self._proc, method, params, self._next_id())

    # ---- HTTP/SSE transport ----
    def _rpc_http(self, method: str, params: dict) -> Any:
        import requests  # lazy import
        if not self.url:
            raise MCPServerError(f"extension server '{self.name}' has no url")
        payload = {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params}
        headers = {"Accept": "application/json, text/event-stream"}
        if self.transport == "streamable_http" and self._session_id:
            headers["mcp-session-id"] = self._session_id
        resp = requests.post(self.url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        sid = resp.headers.get("mcp-session-id")
        if sid:
            self._session_id = sid
        ctype = resp.headers.get("content-type", "")
        if "text/event-stream" in ctype:
            return self._parse_sse(resp.text)
        body = (resp.text or "").strip()
        if not body:
            return {}
        try:
            data = resp.json()
        except ValueError as e:
            raise MCPServerError(
                f"extension server '{self.name}' returned non-JSON: {body[:120]!r}"
            ) from e
        if not isinstance(data, dict):
            raise MCPServerError(
                f"extension server '{self.name}' returned non-object JSON: {body[:120]!r}"
            )
        if "error" in data:
            raise MCPServerError(str(data["error"]))
        return data.get("result", {})

    def _parse_sse(self, text: str) -> Any:
        """Parse a Server-Sent Events body into the first `data:` JSON payload."""
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                payload = line[len("data:"):].strip()
                if not payload or payload == "[DONE]":
                    continue
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if "error" in obj:
                    raise MCPServerError(str(obj["error"]))
                if "result" in obj:
                    return obj.get("result")
                if "id" not in obj:
                    continue  # notification
                return obj.get("result", {})
        return {}

    def _rpc(self, method: str, params: dict) -> Any:
        if self.url:
            return self._rpc_http(method, params)
        return self._rpc_stdio(method, params)

    def list_tools(self) -> list[dict]:
        result = self._rpc("tools/list", {})
        return result.get("tools", [])

    def call_tool(self, tool: str, arguments: dict) -> Any:
        return self._rpc("tools/call", {"name": tool, "arguments": arguments})

    def close(self) -> None:
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
            self._proc = None


class MCPManager:
    """Manage multiple MCP servers from config."""

    def __init__(self):
        self._servers = {}

    def load(self, server_configs: list[dict]) -> None:
        for cfg in server_configs:
            name = cfg.get("name")
            if not name:
                continue
            self._servers[name] = MCPServer(
                name=name,
                command=cfg.get("command"),
                url=cfg.get("url"),
                env=cfg.get("env"),
                transport=cfg.get("transport", "http"),
            )

    def list_servers(self) -> list[str]:
        return list(self._servers)

    def list_tools(self, server: str) -> list[dict]:
        srv = self._servers.get(server)
        if not srv:
            raise MCPServerError(f"extension server not configured: {server}")
        return srv.list_tools()

    def call(self, server: str, tool: str, arguments: dict) -> Any:
        srv = self._servers.get(server)
        if not srv:
            raise MCPServerError(f"MCP server not configured: {server}")
        return srv.call_tool(tool, arguments)

    def close_all(self) -> None:
        for s in self._servers.values():
            s.close()

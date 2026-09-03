"""Tests for the extension bridge skill and Vosk STT (no audio/network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.skills.base import SkillRegistry
from assistant.skills.mcp_bridge import make_mcp_skill


class FakeMCPManager:
    def __init__(self, result=None):
        self.result = result if result is not None else {"ok": True}
        self.calls = []

    def call(self, server, tool, args):
        self.calls.append((server, tool, args))
        return self.result


def _reg(mcp):
    reg = SkillRegistry()
    reg.register(make_mcp_skill(mcp))
    return reg


def test_mcp_bridge_routes():
    mcp = FakeMCPManager()
    reg = _reg(mcp)
    skill, params = reg.route("调用 extension fs read_file {\"path\": \"/x\"}")
    assert skill.name == "mcp_call"
    assert params.get("server") == "fs"
    assert params.get("tool") == "read_file"


def test_mcp_bridge_runs_json_args():
    mcp = FakeMCPManager()
    reg = _reg(mcp)
    skill = reg.find("mcp_call")
    out = skill.run({"server": "fs", "tool": "read_file",
                     "args": '{"path": "/x"}'}, None)
    assert "ok" in out
    assert mcp.calls == [("fs", "read_file", {"path": "/x"})]


def test_mcp_bridge_non_json_args_fallback():
    mcp = FakeMCPManager()
    reg = _reg(mcp)
    skill = reg.find("mcp_call")
    result = skill.run({"server": "fs", "tool": "wakevoice", "args": "hello"}, None)
    assert result
    # non-JSON args fall back to {"input": "hello"}
    assert mcp.calls == [("fs", "wakevoice", {"input": "hello"})]


def test_mcp_bridge_error_returns_friendly():
    class Boom:
        def call(self, server, tool, args):
            raise RuntimeError("connection refused")
    reg = _reg(Boom())
    skill = reg.find("mcp_call")
    out = skill.run({"server": "fs", "tool": "x", "args": "{}"}, None)
    assert "失败" in out


def test_vosk_stt_recognize_bytes(monkeypatch, tmp_path):
    """VoskSTT.recognize_bytes finalizes and returns recognized text."""
    import json as _json
    import types

    fake_vosk = types.ModuleType("vosk")

    class _FakeRec:
        def __init__(self, *a, **k):
            pass
        def AcceptWaveform(self, pcm):
            pass
        def FinalResult(self):
            return _json.dumps({"text": "你好世界"})

    class _FakeModel:
        def __init__(self, path):
            self.path = path

    fake_vosk.Model = _FakeModel
    fake_vosk.KaldiRecognizer = _FakeRec
    monkeypatch.setitem(sys.modules, "vosk", fake_vosk)

    from assistant.stt.vosk_stt import VoskSTT

    (tmp_path / "model").mkdir()
    stt = VoskSTT(tmp_path / "model", 16000, "zh-CN")
    assert stt.recognize_bytes(b"\x00\x01") == "你好世界"
    stt.close()
    assert stt._model is None


def test_vosk_stt_missing_model_raises(monkeypatch, tmp_path):
    """A missing model directory raises STTError on first access."""
    import pytest

    from assistant.core.errors import STTError
    from assistant.stt.vosk_stt import VoskSTT

    stt = VoskSTT(tmp_path / "does-not-exist", 16000, "zh-CN")
    with pytest.raises(STTError):
        _ = stt.model

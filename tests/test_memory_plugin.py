"""Tests for conversation memory and plugin loading."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.core.memory_ctx import Memory
from assistant.skills.plugins import load_plugin_dir


def test_memory_bounds():
    m = Memory(max_turns=4)
    for i in range(10):
        m.add("user", f"msg{i}")
    assert len(m) == 4
    msgs = m.to_messages()
    assert msgs[-1]["content"] == "msg9"


def test_memory_skips_blank():
    m = Memory(max_turns=4)
    m.add("user", "   ")
    m.add("assistant", "")
    assert len(m) == 0


def test_memory_clear():
    m = Memory(max_turns=4)
    m.add("user", "hi")
    m.clear()
    assert len(m) == 0



def test_memory_clamps_non_positive_max_turns():
    """max_turns <= 0 (e.g. 0 or -3 from a bad env var) must not crash deque()."""
    for bad in (0, -3):
        m = Memory(max_turns=bad)
        m.add("user", "hi")
        assert len(m) >= 1
        assert m.to_messages()[0]["content"] == "hi"

def test_memory_clamps_non_numeric_max_turns():
    """max_turns that is not an int (e.g. "abc") must not crash deque()."""
    m = Memory(max_turns="abc")
    m.add("user", "hi")
    assert len(m) >= 1
    assert m._limit == 10

def test_plugin_dir_loads(tmp_path):
    from assistant.skills.base import SkillRegistry
    (tmp_path / "my_skill.py").write_text(
        "from assistant.skills.base import Skill\n"
        "def register_skills(r):\n"
        "    r.register(Skill(name='x', description='d', patterns=['xxx'], handler=lambda p,c:'ok'))\n",
        encoding="utf-8",
    )
    reg = SkillRegistry()
    n = load_plugin_dir(reg, tmp_path)
    assert n == 1
    assert any(m["name"] == "x" for m in reg.all_manifests())

def test_memory_is_truthy_when_empty():
    m = Memory(max_turns=4)
    assert bool(m) is True  # empty memory must still be truthy so agent records turns
    m.add("user", "hi")
    assert bool(m) is True
    assert len(m) == 1

def test_all_manifests_are_json_serializable():
    """all_manifests must be JSON-serializable (compiled patterns -> strings)."""
    import json

    from assistant.skills import control as C
    from assistant.skills.base import SkillRegistry
    reg = SkillRegistry()
    C.register_control_skills(reg)
    manifests = reg.all_manifests()
    # no compiled Pattern objects should leak
    assert all(isinstance(p, str) for m in manifests for p in m["patterns"])
    json.dumps(manifests)  # must not raise
    # the click pattern keeps its named groups for later reconstruction
    click = next(m for m in manifests if m["name"] == "click")
    assert "?P<x>" in click["patterns"][0]


def test_skill_registry_find_unregister():
    from assistant.skills.base import Skill, SkillRegistry
    reg = SkillRegistry()
    reg.register(Skill(name="a", description="d", patterns=["aaa"], handler=lambda p, c: "ok"))
    assert reg.find("a") is not None
    assert reg.find("missing") is None
    assert reg.unregister("a") is True
    assert reg.unregister("a") is False
    assert reg.find("a") is None

def test_memory_save_load(tmp_path):
    m = Memory(max_turns=4)
    m.add("user", "hi")
    m.add("assistant", "yo")
    f = tmp_path / "mem.json"
    m.save(f)
    m2 = Memory(max_turns=4)
    m2.load(f)
    assert len(m2) == 2
    assert m2.to_messages()[0]["content"] == "hi"

def test_screen_reader_backend_validation():
    """ScreenReader rejects unsupported backends on capture."""
    import pytest

    from assistant.screen.reader import ScreenReader
    r = ScreenReader(backend="bogus")
    with pytest.raises(ValueError):
        r.capture("/tmp/x.png")


def test_memory_save_creates_parent_dirs(tmp_path):
    """Memory.save must create nested parent directories."""
    m = Memory(max_turns=4)
    m.add("user", "hi")
    nested = tmp_path / "a" / "b" / "mem.json"
    m.save(nested)
    assert nested.exists()
    m2 = Memory(max_turns=4)
    m2.load(nested)
    assert m2.to_messages()[0]["content"] == "hi"


def test_mcp_sse_parse_and_session():
    """MCPServer handles streamable_http session id and SSE payloads."""
    from assistant.connectors.client import MCPServer

    class FakeResp:
        def __init__(self, text="", headers=None, status=200):
            self.text = text
            self.headers = headers or {}
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError("http error")

        def json(self):
            import json
            return json.loads(self.text)

    srv = MCPServer(name="x", url="http://example.com", transport="streamable_http")
    # _parse_sse should extract result and ignore notifications
    sse = (
        "data: {\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}\n\n"
        "data: {\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"tools\":[]}}\n\n"
    )
    assert srv._parse_sse(sse) == {"tools": []}
    # no-data SSE returns empty dict
    assert srv._parse_sse("data: [DONE]\n\n") == {}


def test_rpc_http_non_json_body_raises_clean(monkeypatch):
    """A non-JSON HTTP response must raise MCPServerError, not ValueError."""
    import requests

    from assistant.connectors.client import MCPServer
    from assistant.core.errors import MCPServerError

    class FakeResp:
        text = "<html>gateway error</html>"
        headers = {}
        def raise_for_status(self):
            pass
        def json(self):
            raise ValueError("no json")

    monkeypatch.setattr(requests, "post",
                        lambda *a, **k: FakeResp())
    srv = MCPServer(name="x", url="http://example.com", transport="http")
    try:
        srv._rpc_http("ping", {})
        raised = False
    except MCPServerError as e:
        raised = True
        assert "non-JSON" in str(e)
    assert raised


def test_rpc_http_empty_body_returns_empty(monkeypatch):
    """An empty 200 response body yields {} rather than crashing."""
    import requests

    from assistant.connectors.client import MCPServer

    class FakeResp:
        text = ""
        headers = {}
        def raise_for_status(self):
            pass
        def json(self):
            raise ValueError("no json")

    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResp())
    srv = MCPServer(name="x", url="http://example.com", transport="http")
    assert srv._rpc_http("ping", {}) == {}


def test_stdio_send_skips_non_json_lines(monkeypatch):
    """stdio transport must tolerate non-JSON lines between responses."""
    from assistant.connectors.client import MCPServer

    class _Stdout:
        def __init__(self, lines):
            self._it = iter(lines)
        def readline(self):
            try:
                return next(self._it)
            except StopIteration:
                return ""

    class _Stdin:
        def __init__(self):
            self.written = []
        def write(self, s):
            self.written.append(s)
        def flush(self):
            pass

    class FakeProc:
        def __init__(self, lines):
            self.stdout = _Stdout(lines)
            self.stdin = _Stdin()

    srv = MCPServer(name="x", command=["python", "-c", "pass"], transport="stdio")
    proc = FakeProc(["not json\n", '{"jsonrpc":"2.0","id":1,"result":{"ok":true}}\n'])
    result = srv._send_stdio(proc, "ping", {}, 1)
    assert result == {"ok": True}


def test_word_matches_exact_and_fuzzy():
    """The wake matcher handles exact matches and sensitivity-gated fuzzy ones."""
    from assistant.wake.keyword import _word_matches
    # exact substring always matches
    assert _word_matches("土豆", "叫土豆同学", 0.5) is True
    # empty word never matches
    assert _word_matches("", "土豆", 0.5) is False
    # sensitivity == 1 disables fuzzy matching
    assert _word_matches("土豆", "土逗", 1.0) is False
    # low sensitivity allows a near-homophone
    assert _word_matches("土豆", "土逗", 0.5) is True
    # very different text never matches
    assert _word_matches("土豆", "今天天气不错", 0.3) is False

def test_create_wake_factory_keyword(monkeypatch):
    """create_wake factory builds a KeywordWake with a reused model (no mic)."""
    import sys
    import types

    # Inject fake vosk modules so KeywordWake does not load a real model.
    fake_vosk = types.ModuleType("vosk")
    fake_vosk.Model = object
    class _FakeRec:
        def __init__(self, *a, **k):
            pass
        def SetWords(self, *a, **k):
            pass
    fake_vosk.KaldiRecognizer = _FakeRec
    monkeypatch.setitem(sys.modules, "vosk", fake_vosk)

    from assistant.wake.keyword import KeywordWake, create_wake

    w = create_wake("你好伙伴", "unused-dir", 16000, 0.5, backend="keyword", model=object())
    assert isinstance(w, KeywordWake)
    assert w.word == "你好伙伴"
    assert w._model is not None
    assert w.sample_rate == 16000
    assert w.sensitivity == 0.5

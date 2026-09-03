"""Tests for the CLI entry point (mocked Assistant, no audio/network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from assistant import cli


class FakeAssistant:
    """Stands in for assistant.core.app.Assistant during CLI tests."""

    def __init__(self, config_path=None):
        self.config_path = config_path
        self.spoken = []
        self.handled = []
        self.skills = _FakeSkills()
        self.agents = _FakeAgents()

    def shutdown(self):
        self.shutdown_called = True

    def speak(self, text, emotion=None):
        self.spoken.append((text, emotion))

    def handle_text(self, text):
        self.handled.append(text)
        return ("你好", "happy")

    def run_once(self):
        self.ran_once = True

    def run_wake_loop(self):
        self.ran_wake = True


class _FakeSkills:
    def all_manifests(self):
        return [{"name": "s1", "description": "d1"}]


class _FakeAgents:
    def names(self):
        return ["general"]


@pytest.fixture
def fake_app(monkeypatch):
    created = {}
    def factory(config_path=None):
        created["app"] = FakeAssistant(config_path)
        return created["app"]
    # `Assistant` is imported inside main(), so patch the real module attribute.
    from assistant.core import app as app_module
    monkeypatch.setattr(app_module, "Assistant", factory)
    return created


def test_list_skills_exit_zero(fake_app, capsys):
    assert cli.main(["--list-skills"]) == 0
    out = capsys.readouterr().out
    assert "s1" in out
    assert fake_app["app"].shutdown_called


def test_list_agents_exit_zero(fake_app, capsys):
    assert cli.main(["--list-agents"]) == 0
    out = capsys.readouterr().out
    assert "general" in out
    assert fake_app["app"].shutdown_called


def test_text_path_speaks_reply(fake_app):
    assert cli.main(["--text", "你好"]) == 0
    app = fake_app["app"]
    assert app.handled == ["你好"]
    assert app.spoken == [("你好", "happy")]
    assert app.shutdown_called


def test_speak_path(fake_app):
    assert cli.main(["--speak", "测试"]) == 0
    assert fake_app["app"].spoken == [("测试", None)]
    assert fake_app["app"].shutdown_called


def test_default_runs_wake_loop(fake_app):
    assert cli.main([]) == 0
    assert fake_app["app"].ran_wake
    assert fake_app["app"].shutdown_called


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0

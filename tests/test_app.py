"""Tests for the top-level Assistant wiring (no audio/network)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.core.app import Assistant
from assistant.core.llm import LLMClient


def _assistant():
    return Assistant()


def test_llm_disabled_without_key(monkeypatch):
    """With no base_url and no API key, llm must be None (instant local fallback)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    a = _assistant()
    a.config.set("llm.base_url", None)
    a.config.set("llm.enabled", True)
    assert a.llm is None


def test_llm_enabled_with_base_url(monkeypatch):
    """A custom base_url (Ollama/vLLM etc.) enables LLM without an API key."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    a = _assistant()
    a.config.set("llm.base_url", "http://localhost:11434/v1")
    a.config.set("llm.enabled", True)
    assert isinstance(a.llm, LLMClient)


def test_llm_enabled_with_api_key(monkeypatch):
    """An API key env var enables LLM."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    a = _assistant()
    a.config.set("llm.base_url", None)
    a.config.set("llm.enabled", True)
    assert isinstance(a.llm, LLMClient)


def test_llm_explicitly_disabled(monkeypatch):
    """llm.enabled=false forces None even when a key is present."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    a = _assistant()
    a.config.set("llm.enabled", False)
    assert a.llm is None

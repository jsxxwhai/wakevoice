"""Skill framework: discoverable, self-describing capabilities.

A skill is any callable object with:
- `name`: stable identifier
- `patterns`: list of trigger regex/str for intent matching
- `run(args, ctx)`: performs the action and returns a response
Skills register themselves and expose a manifest for the LLM/intent router.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable


log = logging.getLogger(__name__)


@dataclass
class SkillContext:
    """Runtime context passed to every skill (config, say, etc.)."""
    config: Any = None
    speak: Callable[[str, str | None], Any] | None = None
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    name: str
    description: str
    patterns: list[str]
    handler: Callable[[dict[str, Any], SkillContext], str]
    keywords: list[str] = field(default_factory=list)

    def match(self, text: str) -> dict[str, Any] | None:
        """Return match params if this skill should fire, else None.

        Regex patterns take priority (they can extract named params like
        `target`). Keywords act only as a fallback trigger.
        """
        for pat in self.patterns:
            if hasattr(pat, "search"):  # compiled pattern
                m = pat.search(text)
            else:
                m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.groupdict() or {"text": text}
        lowered = text.lower()
        for kw in self.keywords:
            if kw and kw.lower() in lowered:
                return {"text": text}
        return None

    def run(self, params: dict[str, Any], ctx: SkillContext) -> str:
        return self.handler(params, ctx)


class SkillRegistry:
    """Ordered registry of skills; later skills override earlier matches."""

    def __init__(self):
        self._skills: list[Skill] = []

    def register(self, skill: Skill) -> None:
        self._skills.append(skill)

    def register_func(self, name, description, patterns, keywords=None):
        def deco(fn):
            self.register(Skill(name, description, patterns, fn, keywords or []))
            return fn
        return deco

    def route(self, text: str) -> tuple[Skill, dict[str, Any]] | None:
        for skill in reversed(self._skills):
            params = skill.match(text)
            if params is not None:
                return skill, params
        return None

    def find(self, name: str) -> Skill | None:
        for s in self._skills:
            if s.name == name:
                return s
        return None

    def unregister(self, name: str) -> bool:
        for i, s in enumerate(self._skills):
            if s.name == name:
                del self._skills[i]
                return True
        return False

    def all_manifests(self) -> list[dict[str, Any]]:
        """Return JSON-serializable manifests (compiled patterns -> strings)."""
        def _pats(skill: Skill) -> list[str]:
            out = []
            for pat in skill.patterns:
                if hasattr(pat, "pattern"):  # compiled re.Pattern
                    out.append(pat.pattern)
                else:
                    out.append(str(pat))
            return out

        return [
            {"name": s.name, "description": s.description,
             "patterns": _pats(s), "keywords": s.keywords}
            for s in self._skills
        ]

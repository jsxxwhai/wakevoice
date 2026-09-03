"""Short-term conversation memory: a bounded deque of recent turns."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class Memory:
    """Bounded ring buffer of (role, text) turns.

    Keeps the most recent `max_turns` exchanges so an LLM can refer back to
    earlier context without unbounded growth (which would raise latency and
    token cost).
    """

    max_turns: int = 10

    def __post_init__(self):
        # A non-positive or non-numeric max_turns (e.g. 0 or "abc" from a
        # misconfigured env var) must not crash deque(); clamp to >= 1.
        try:
            n = int(self.max_turns)
        except (TypeError, ValueError):
            n = 10
        self._limit = max(1, n)
        self._history = deque(maxlen=self._limit)

    def add(self, role: str, text: str) -> None:
        if text and text.strip():
            self._history.append({"role": role, "content": text.strip()})

    def to_messages(self) -> list[dict]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()

    def save(self, path) -> None:
        """Persist history to a JSON file (creating parent dirs as needed)."""
        import json
        from pathlib import Path
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(list(self._history), ensure_ascii=False), encoding="utf-8")

    def load(self, path) -> None:
        """Load history from a JSON file (best-effort, no crash on missing)."""
        import json
        from pathlib import Path
        p = Path(path)
        if not p.exists():
            return
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._history.clear()
                for item in data[-self._limit:]:
                    if isinstance(item, dict):
                        self._history.append({"role": item.get("role", "user"), "content": item.get("content", "")})
        except (json.JSONDecodeError, OSError):
            pass

    def __len__(self) -> int:
        return len(self._history)

    def __bool__(self) -> bool:
        # A Memory object is always truthy; emptiness is not falseness.
        # This mirrors the "is not None" checks in the agent so an empty
        # (but present) memory still records turns.
        return True

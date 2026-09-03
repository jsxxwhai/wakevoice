"""Configuration system: layered YAML config with dot-path access and hot reload."""
from __future__ import annotations

import copy
import os
import threading
from pathlib import Path
from typing import Any

import yaml

from ..core.errors import ConfigError


class Config:
    """Layered configuration with defaults + user overrides.

    Priority (low -> high): built-in defaults -> user config.yaml -> env vars.
    Supports dot-path lookup (`cfg.get("tts.engine")`) and runtime set.
    Thread-safe for read/write; optional file watching for hot reload.
    """

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else None
        self._lock = threading.RLock()
        self._data: dict[str, Any] = {}
        self._defaults: dict[str, Any] = self._builtin_defaults()
        self.reload()

    @staticmethod
    def _builtin_defaults() -> dict[str, Any]:
        return {
            "app": {"name": "WakeVoice", "log_level": "INFO"},
            # `backends` is the list of valid wake engines; `engine` must be
            # one of these (validated when the wake detector is created).
            "wake": {"engine": "keyword", "word": "你好伙伴", "sensitivity": 0.5,
                     "backends": ["keyword", "openwakeword"]},
            "stt": {"engine": "vosk", "model_dir": "vosk-model-small-cn-0.22",
                    "sample_rate": 16000, "language": "zh-CN"},
            "tts": {"engine": "edge", "voice": "zh-CN-XiaoxiaoNeural", "rate": "+0%",
                    "pitch": "+0Hz", "volume": "+0%", "style": "general",
                    "emotion_enabled": True, "pyttsx3_rate": 175,
                    "pyttsx3_volume": 0.9},
            "llm": {"base_url": None, "api_key_env": "OPENAI_API_KEY",
                    "model": "gpt-4o-mini", "temperature": 0.7,
                    "timeout": 20.0, "enabled": True},
            "skills": {"enabled": True, "disabled": [], "plugin_dir": "skills"},
            "agents": {"max_workers": 4, "default_agent": "general"},
            "mcp": {"servers": [], "auto_discover": True},
            "screen": {"backend": "mss", "ocr_enabled": True, "ocr_lang": "chi_sim+eng"},
            # Safety railings: screen-affecting system operations stay
            # disabled until the user explicitly opts in; runtime temp files
            # live under the project workspace instead of the system drive.
            "safety": {
                "allow_screen_control": False,
                "runtime_dir": "runtime_tmp",
                "max_temp_mb": 50,
                "cleanup_on_start": True,
            },
            # Hands-free voice loop settings
            "voice": {"mode": "hands_free", "hold_key": "space",
                     "silence_seconds": 1.5,
                     "stop_key": "esc", "stop_enabled": True},
            "memory": {"max_turns": 10, "file": ""},
        }

    # ---- loading ----
    def reload(self) -> None:
        with self._lock:
            data = copy.deepcopy(self._defaults)
            if self._path and self._path.exists():
                try:
                    loaded = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
                    if not isinstance(loaded, dict):
                        raise ConfigError(f"config root must be a mapping: {self._path}")
                    data = self._deep_merge(data, loaded)
                except yaml.YAMLError as e:
                    raise ConfigError(f"invalid YAML in {self._path}: {e}") from e
            self._data = data

    def _deep_merge(self, base: dict, override: dict) -> dict:
        out = copy.deepcopy(base)
        for k, v in override.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = self._deep_merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
        return out

    # ---- access ----
    def _coerce(self, value: str, reference: Any) -> Any:
        """Coerce an env-var string to the type of the config reference value."""
        if reference is None or value is None:
            return value
        if isinstance(reference, bool):
            return str(value).strip().lower() in ("1", "true", "yes", "on", "y")
        if isinstance(reference, int):
            try:
                return int(str(value).strip())
            except ValueError:
                return value
        if isinstance(reference, float):
            try:
                return float(str(value).strip())
            except ValueError:
                return value
        return value

    def _lookup(self, key: str, default: Any) -> Any:
        node: Any = self._data
        for part in key.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def get(self, key: str, default: Any = None) -> Any:
        """Dot-path lookup, e.g. `cfg.get('tts.engine')`.

        Priority (low -> high): built-in defaults -> user config.yaml -> env
        vars. An env var named like `WAKE_WORD` overrides `wake.word`; this is
        how you inject secrets (e.g. `LLM_API_KEY`) without editing the file.
        Numeric/boolean env values are coerced to the config reference type.
        """
        with self._lock:
            # 1) env var (highest priority) when explicitly set
            env_name = key.upper().replace(".", "_")
            env_val = os.environ.get(env_name)
            if env_val is not None:
                return self._coerce(env_val, self._lookup(key, default))
            # 2) nested config value
            return self._lookup(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            node = self._data
            parts = key.split(".")
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = value

    def as_dict(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._data)

    def save(self) -> None:
        if not self._path:
            return
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                yaml.safe_dump(self._data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

    def __repr__(self) -> str:
        return f"Config(path={self._path!r})"

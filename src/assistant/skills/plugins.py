"""Local plugin auto-discovery: drop a .py with `register_skills(registry)` into the skills dir."""
from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def load_plugin_dir(registry, directory: str | Path) -> int:
    """Import every `*.py` in `directory` that exposes `register_skills(registry)`.

    Returns the number of plugins loaded. A plugin file looks like::

        def register_skills(registry):
            from assistant.skills.base import Skill
            registry.register(Skill(name="hello", description="...",
                                    patterns=["你好"], handler=lambda p, c: "你好呀"))

    Each plugin is loaded in its own module namespace (isolated, safe-ish) and
    only `register_skills` is invoked; exceptions are logged and skipped.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0
    loaded = 0
    for py in sorted(directory.glob("*.py")):
        if py.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"wakevoice_plugin_{py.stem}", py)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            register = getattr(mod, "register_skills", None)
            if callable(register):
                register(registry)
                loaded += 1
                log.info("loaded plugin %s", py.name)
        except Exception as e:
            log.warning("failed to load plugin %s: %s", py.name, e)
    return loaded

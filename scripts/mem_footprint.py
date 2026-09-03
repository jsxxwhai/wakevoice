"""Measure assistant memory footprint (import-only vs. fully loaded).

Usage:
  python scripts/mem_footprint.py            # report import-only + full load
  python scripts/mem_footprint.py --json      # machine-readable single line

Prints RSS in MiB using the same helper as assistant.core.memory.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from assistant.core.memory import current_rss_mb, format_mem  # noqa: E402


def measure_import_only() -> float:
    import assistant.core.app  # noqa: F401 - force import without instantiation
    return current_rss_mb()


def measure_full_load() -> float:
    from assistant.core.app import Assistant
    app = Assistant()
    # touch lazy subsystems that are cheap and non-audio (LLM stays unloaded)
    _ = app.skills.all_manifests()
    _ = app.agents.names()
    rss = current_rss_mb()
    app.shutdown()
    return rss


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="measure assistant RSS footprint")
    ap.add_argument("--json", action="store_true", help="emit a single JSON line")
    args = ap.parse_args(argv)

    import_only = measure_import_only()
    full = measure_full_load()

    if args.json:
        print(json.dumps({"import_only_mib": round(import_only, 2),
                          "full_load_mib": round(full, 2)}))
    else:
        print("import-only RSS :", format_mem(import_only))
        print("full-load RSS   :", format_mem(full))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

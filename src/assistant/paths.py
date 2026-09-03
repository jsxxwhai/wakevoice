"""Filesystem anchor helpers.

The app ships two ways:

* source / green-folder build  -> the project root is the data root
* PyInstaller bundle           -> data lives next to the executable
  (onedir) or in the onefile temp extraction dir

All relative paths in the default config (speech model, plugin dir,
runtime scratch dir) are resolved against this anchor so the app works
no matter where it is launched from.
"""
from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    """Return the directory that holds the project's data files.

    - Normal source runs: the repository root (parent of ``src/assistant``).
    - PyInstaller onefile: the ``_MEIPASS`` extraction dir (read-only,
      bundled model lives there if included).
    - PyInstaller onedir: the directory containing the executable.
    """
    # PyInstaller onefile extraction dir
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base)
    # PyInstaller onedir: exe lives in the bundle root
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # source run: repo root = grandparent of src/assistant/paths.py
    return Path(__file__).resolve().parent.parent.parent


def data_dir() -> Path:
    """Directory where writable runtime data may be created.

    Under a frozen onefile bundle the extraction dir is read-only, so writable
    data (runtime scratch) goes next to the executable instead.
    """
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        return Path(sys.executable).resolve().parent
    return app_root()


def resolve(path: str | Path | None) -> Path | None:
    """Resolve a possibly-relative config path against the app anchor."""
    if path is None:
        return None
    p = Path(path)
    if p.is_absolute():
        return p
    return app_root() / p

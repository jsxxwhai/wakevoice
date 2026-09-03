"""Create a GitHub Release for OpenVoice Desktop from the local CLI.

This is a thin, safe wrapper around the GitHub CLI. It never uploads a token,
never guesses a repository, and stops with a clear message if the environment
is not ready.

Prerequisites (one-time):
  1. git config user.name  "Your Name"
  2. git config user.email "you@example.com"
  3. gh auth login          (then re-run this script)
  4. git remote add origin https://github.com/jsxxwhai/openvoice-desktop

Usage:
  python scripts/publish_github.py            # create a release for HEAD
  python scripts/publish_github.py v0.1.1     # create a release for a tag
"""
from __future__ import annotations

import subprocess
import sys

APP = "openvoice-desktop"


def _run(args, check=True):
    """Run a command and return (returncode, stdout, stderr) as text."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "", f"command not found: {args[0]}"
    if check and proc.returncode != 0:
        print(proc.stderr.strip(), file=sys.stderr)
        sys.exit(proc.returncode)
    return proc.returncode, proc.stdout, proc.stderr


def main(argv=None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    if len(args) > 1:
        print("usage: python scripts/publish_github.py [TAG]", file=sys.stderr)
        return 2

    # 1) gh must exist and be authenticated
    code, _, err = _run(["gh", "--version"], check=False)
    if code != 0:
        print("[publish] GitHub CLI (gh) is required.", file=sys.stderr)
        print("Install: https://cli.github.com/  then run: gh auth login", file=sys.stderr)
        return 1
    code, _, _err = _run(["gh", "auth", "status"], check=False)
    if code != 0:
        print("[publish] You are not logged in to GitHub.", file=sys.stderr)
        print("Run: gh auth login", file=sys.stderr)
        return 1

    # 2) a git remote must exist so gh knows the repository
    code, out, _ = _run(["git", "remote", "-v"], check=False)
    if code != 0 or not out.strip():
        print("[publish] No git remote is configured.", file=sys.stderr)
        print('Example: git remote add origin https://github.com/jsxxwhai/openvoice-desktop', file=sys.stderr)
        return 1

    tag = args[0] if args else None
    if not tag:
        # default to the most recent version tag on the current branch
        code, out, _ = _run(["git", "describe", "--tags", "--abbrev=0"], check=False)
        if code != 0 or not out.strip():
            print("[publish] No version tag found. Tag first, e.g.: git tag v0.1.1", file=sys.stderr)
            return 1
        tag = out.strip()
        print(f"[publish] using latest tag: {tag}")

    # 3) build artifacts (optional but useful for a release)
    print("[publish] building distributions ...")
    code, _, _ = _run([sys.executable, "-m", "pip", "install", "--quiet", "build"], check=False)
    code2, _, _err2 = _run([sys.executable, "-m", "build"], check=False)
    if code != 0 or code2 != 0:
        print("[publish] build step failed; continuing with source-only release.", file=sys.stderr)
        assets = []
    else:
        import glob
        assets = sorted(glob.glob("dist/*.tar.gz") + glob.glob("dist/*.whl"))

    # 4) create the release
    title = tag.removeprefix("v")
    cmd = ["gh", "release", "create", tag, "--title", f"{APP} {title}",
           "--notes", "See CHANGELOG.md for details."]
    cmd += assets
    print("[publish] creating release ...")
    _run(cmd)
    print(f"[publish] done: https://github.com/jsxxwhai/{APP}/releases/tag/{tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

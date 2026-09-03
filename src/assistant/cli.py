"""Command-line entry point for the assistant."""
from __future__ import annotations

import argparse
import sys


def main(argv=None) -> int:
    # Windows consoles often default to a non-UTF-8 codepage (e.g. GBK),
    # which garbles the Chinese skill/agent descriptions. Force UTF-8 stdout
    # so list/help output renders correctly regardless of the console locale.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    parser = argparse.ArgumentParser(prog="wakevoice", description="WakeVoice voice assistant")
    parser.add_argument("-c", "--config", help="path to config.yaml")
    parser.add_argument("--once", action="store_true", help="single push-to-talk exchange")
    parser.add_argument("--wake", action="store_true", help="continuous wake-word loop")
    parser.add_argument("--list-skills", action="store_true", help="list registered skills")
    parser.add_argument("--list-agents", action="store_true", help="list agents")
    from . import __version__
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--text", help="process one text utterance directly (no mic)")
    parser.add_argument("--speak", help="speak a line and exit (test TTS)")
    args = parser.parse_args(argv)

    from .core.app import Assistant
    app = Assistant(args.config)

    if args.list_skills:
        try:
            for m in app.skills.all_manifests():
                print(f"- {m['name']}: {m['description']}")
        finally:
            app.shutdown()
        return 0
    if args.list_agents:
        try:
            for n in app.agents.names():
                print(f"- {n}")
        finally:
            app.shutdown()
        return 0
    if args.once:
        try:
            app.run_once()
        finally:
            app.shutdown()
        return 0
    if args.wake:
        try:
            app.run_wake_loop()
        except KeyboardInterrupt:
            pass
        finally:
            app.shutdown()
        return 0

    if args.text:
        try:
            reply, emotion = app.handle_text(args.text) or ("", "neutral")
            app.speak(reply, emotion)
        finally:
            app.shutdown()
        return 0
    if args.speak:
        try:
            app.speak(args.speak)
        finally:
            app.shutdown()
        return 0
    # default: wake loop
    try:
        app.run_wake_loop()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())

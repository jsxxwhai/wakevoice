# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

(no unreleased changes yet)

## [0.2.0] - 2026-09-03

### Added
- Hands-free voice mode (default): speak, pause, and the assistant acts — no
  push-to-talk key required. Push-to-talk remains available via
  `voice.mode: push_to_talk`.
- Configurable global **stop key** (`voice.stop_key`, default `Esc`) that
  interrupts speech and aborts in-progress listening; can be disabled with
  `voice.stop_enabled: false`.
- Project-local runtime temp directory (`safety.runtime_dir`) with automatic
  cleanup and a size cap, avoiding writes to the OS temp drive.
- `scripts/publish_github.py` and a GitHub Actions release workflow that run
  tests/lint before building wheels and creating a GitHub Release on `v*` tags.

### Changed
- Wake-word flow is now hands-free first: after the wake response you speak a
  command directly and pause to finish.
- Public-facing branding and docs were neutralized (no third-party assistant
  names, personas, or trademarks).
- Internal code identifiers renamed from "Echo" to "WakeVoice" (default app
  name, CLI program name, thread names, temp-audio prefix, plugin module prefix).
- Wake-word idle behavior: pressing the stop key while idle cancels the
  blocking wake listen and returns cleanly instead of leaving a stale listener.

### Fixed
- Stop-key handling during wake listening no longer leaves a dangling abort
  callback or a partially aborted recognizer.
- Removed stale `_rewrite*.py` scratch files and an outdated build artifact
  (egg-info) directory.

## [0.1.1] - 2026-08-31

### Added
- GitHub community files: `CODE_OF_CONDUCT.md`, `SECURITY.md`, issue/PR
  templates.
- CI matrix runs on Linux and Windows (Python 3.10/3.11/3.12).
- Bilingual README with feature overview, voice modes, skills table, and
  roadmap.

### Changed
- `wake.backends` is a validated list of allowed engines; the default
  (`keyword`) is validated against it. Removed the dead `app.autostart` field.
- `pyproject.toml` dependency list now matches `scripts/bootstrap.py`
  (`keyboard`, `pyperclip`, `pytesseract` added; unused `platformdirs` removed;
  redundant optional groups removed).
- Application/website launch map expanded to cover more sites and apps with a
  longer-key-first matching rule.

### Fixed
- `scripts/bootstrap.py` now installs `keyboard`, so a fresh bootstrap can run
  push-to-talk STT.
- `screenshot` skill writes timestamped PNGs into the user Pictures folder
  instead of polluting the current working directory.
- CLI `--text`, `--speak`, `--list-skills`, `--list-agents`, and `--version`
  now exit cleanly and have test coverage.
- LLM calls without API keys are auto-disabled with a graceful local fallback;
  configurable per-request timeout avoids a 20 s cold stall.
- `wake.sensitivity` is honored by the `keyword` backend for fuzzy wake-word
  matching.
- `skills.enabled: false` now actually skips built-in skill registration.
- `Config.get` honors environment variables as the highest-priority layer.
- `press_keys`/`click`/`type_text` catch automation failures and return a
  friendly message; volume values are clamped to 0–100.

## [0.1.0] - 2026-08-31

### Added
- Pluggable wake-word detection with `keyword` / `openwakeword` backends and
  fully custom wake words.
- Offline Vosk speech-to-text with push-to-talk.
- Emotional text-to-speech (online neural + offline fallback).
- Multi-agent hub and an LLM agent with a multi-turn tool-calling loop.
- Built-in skills: open apps/websites, keyboard/mouse control, volume,
  clipboard, screenshot, file read/write, system info, lock screen, task
  manager, minimize windows, and screen reading with OCR.
- MCP (Model Context Protocol) extension client with stdio/HTTP transports.
- Local plugin auto-discovery.
- Bounded conversation memory with JSON persistence.
- Layered YAML configuration with dot-path access and environment overrides.
- Low-memory lazy-loading design.

### Fixed
- `all_manifests()` returns JSON-serializable manifests (regex patterns are
  converted to strings), fixing extension/LLM tool export.
- `MCPServer` stdio transport uses UTF-8 explicitly so Chinese JSON-RPC
  payloads are not garbled on Windows.
- Clipboard routing no longer misroutes "复制" to unrelated skills.
- `Memory.save` creates parent directories for nested `memory.file` paths.
- `Config.get` returns correct fallbacks and honors environment variables.
- `click` skill no longer fires on a bare "点击" without coordinates.

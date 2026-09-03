# OpenVoice Desktop

> 一个可定制、低内存、多智能体的桌面语音助手。
> 自定义唤醒词 · 情感语音合成 · 控制电脑 · 读取屏幕 · 插件扩展 · 多 Agent。
>
> A customizable, low-memory, multi-agent desktop voice assistant.
> Custom wake word · emotional speech synthesis · control your PC · read your
> screen · pluggable skills · multi-agent orchestration.

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](#)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

If you find this project useful, **give it a Star** ⭐ and share it with
friends. Found a bug or want a feature? Open an
[issue](https://github.com/jsxxwhai/openvoice-desktop/issues).


> [!IMPORTANT]
> This is the public-facing README for the GitHub repository. It deliberately
> avoids third-party product names, logos, or trademarked assistant personas so
> the project can be published without endorsement or affiliation concerns.

## Download

This project ships as **two distributions** — pick whichever fits your machine:

| Distribution | What you get | Requirements | Get it |
|---|---|---|---|
| **Source / green folder** | Full source + `安装并启动.bat` (auto-installs deps & downloads the speech model) | Windows 10/11 + Python 3.10+ | [openvoice-desktop](https://github.com/jsxxwhai/openvoice-desktop/releases) |
| **Portable EXE** | `OpenVoiceDesktop.exe` + bundled runtime; no Python needed. First launch downloads the speech model next to the exe. | Windows 10/11 (64-bit) | [openvoice-desktop-portable](https://github.com/jsxxwhai/openvoice-desktop-portable/releases) |

> Both versions speak the same assistant (wake word “你好伙伴”), and both are fully open source. The portable EXE is built from this repository by `scripts/build_dist.py`.

## Features

- 🎙️ **Custom wake word** — set any word in one line of config; no retraining.
- 🗣️ **Emotional speech** — 9 built-in emotions, online neural voice or offline
  fallback.
- 🖥️ **Control your PC** — launch apps and sites, type text, press hotkeys,
  click, adjust volume, lock the screen, read the screen with OCR.
- 🔌 **Skills & plugins** — drop a `.py` file into `skills/` to add a capability.
- 🤖 **Multi-agent** — register any number of agents and route by role.
- 🧠 **LLM optional** — works fully offline; connect any Chat Completions-compatible
  endpoint when you want richer dialogue.
- 📉 **Low memory** — everything is lazy-loaded; import-only footprint ~14 MiB.

## Quickstart

```bash
# 1. install
python -m pip install -e .
python scripts/bootstrap.py      # downloads the (offline) speech model

# 2. configure
cp config/config.example.yaml config.yaml

# 3. run
python main.py --wake            # wake-word loop
python main.py --once            # single push-to-talk exchange
python main.py --text "hello"    # text mode (no microphone needed)
```

`bootstrap.py` installs Python dependencies and downloads a small Chinese
speech-recognition model (~42 MB) on first run.

## Voice modes

- **Wake word** — say your configured wake word, the assistant answers, then
  you speak your command.
- **Hands-free** — after the wake response, speak and pause; the assistant
  finalizes after a silence gap (`voice.silence_seconds`).
- **Push-to-talk** — hold a key (default Space) while speaking, release to
  finalize (`voice.mode: push_to_talk`).
- **Stop key** — press `Esc` (configurable) at any time to interrupt speech or
  abort listening. Can be disabled via `voice.stop_enabled: false`.

## Safety

Screen-affecting system operations (locking the screen, minimizing all
windows) are **disabled by default**. To enable:

```yaml
safety:
  allow_screen_control: true
```

Runtime temp files (e.g. synthesized audio) are kept inside the project
workspace (`runtime_tmp/`) rather than the OS temp drive, and are capped and
cleaned automatically.

## Configuration

Copy `config/config.example.yaml` to `config.yaml` and edit:

```yaml
wake:
  word: <your-wake-word>     # any word you like

voice:
  mode: hands_free           # hands_free | push_to_talk
  silence_seconds: 1.5       # pause length before the assistant acts
  stop_key: esc
  stop_enabled: true

tts:
  engine: auto               # online neural | offline fallback
  voice: your-voice-profile

llm:
  enabled: true              # set false for a fully offline assistant
  base_url: null             # any Chat Completions-compatible endpoint
```

## Built-in skills

| Skill | Example |
|---|---|
| open_app | "open a text editor", "open example.com" |
| type_text | "type hello world" |
| press_keys | "press ctrl+c" |
| click | "click 100 200" |
| set_volume | "set volume to 80" |
| clipboard | "copy hello", "read clipboard" |
| screenshot | "take a screenshot" |
| read_file / write_file | "read file a.txt" |
| read_screen | "what is on my screen?" |
| system_info | "system info" |
| lock_screen | "lock the screen" (requires opt-in) |
| task_manager | "open task manager" |
| minimize_windows | "show desktop" (requires opt-in) |
| mcp_call | "call extension <name>" |

> Built-in site shortcuts target well-known sites by exact aliases and are
> user-triggered only.

## Plugins

Drop a `.py` file into `skills/` that defines `register_skills(registry)`:

```python
from assistant.skills.base import Skill

def register_skills(registry):
    registry.register(Skill(
        name="hello", description="say hello",
        patterns=["你好插件"],
        handler=lambda p, c: "你好呀！"))
```

## Multi-agent

```python
from assistant.agents.hub import Agent, AgentHub, AgentContext

hub = AgentHub()
hub.register(Agent(name="coder", role="写代码", system_prompt="你是一个程序员"))
ctx = AgentContext()
print(hub.dispatch("coder", "帮我写个快速排序", ctx))
```

## Project layout

```
src/assistant/
├── core/        # config, logging, errors, app assembly
├── skills/      # skills (launch apps, control PC, system utilities…)
├── agents/      # multi-agent framework
├── connectors/  # extension client
├── tts/         # speech synthesis
├── stt/         # speech recognition
├── wake/        # wake-word detection
├── screen/      # screen capture + OCR
└── cli.py       # command-line entry point
```

## Roadmap

- [x] Custom wake word + multiple backends
- [x] Emotional speech synthesis
- [x] Multi-agent + LLM tool calling
- [x] Custom extension client
- [x] Plugin auto-discovery
- [x] Safety railings (opt-in screen control, project-local temp files)
- [ ] GUI configuration editor
- [ ] Wake-word training toolkit
- [ ] Broader platform support (macOS/Linux polish)

## Documentation

- [Architecture](docs/architecture.md)
- [Extending](docs/extending.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## License

[MIT](LICENSE) © OpenVoice Desktop Contributors

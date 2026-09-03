<div align="center">

# 🎙️ OpenVoice Desktop

**对着电脑说话，它就帮你干活。** Hands-free Chinese voice assistant for your desktop.

> 说一句“你好伙伴”，它答应一声；再用嘴说命令，它照做 —— 全程不用碰键盘。
> Wake word → spoken command → done. Runs locally, works offline, no cloud account.

[![Release](https://img.shields.io/github/v/release/jsxxwhai/openvoice-desktop?color=blue&label=Latest%20Release)](https://github.com/jsxxwhai/openvoice-desktop/releases)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/jsxxwhai/openvoice-desktop?style=social)](https://github.com/jsxxwhai/openvoice-desktop)

**Free · Open source · No cloud · No data leaves your PC**

If this project helps you, **give it a Star ⭐** — it motivates us to keep building.

</div>

> [!IMPORTANT]
> This is the public-facing README for the GitHub repository. It deliberately
> avoids third-party product names, logos, or trademarked assistant personas so
> the project can be published without endorsement or affiliation concerns.

## 🚀 What it feels like

```
你：你好伙伴
它：我在。有什么吩咐？
你：打开记事本
   （停顿 1.5 秒）
它：好的，已经打开记事本了。
你：现在几点了？
它：现在是下午 3 点 24 分。
你：拜拜
它：再见，有需要随时叫我。
```

- 🔉 说“你好伙伴”唤醒，它回应“我在”
- 🗣️ 用嘴直接说命令，**停顿 1.5 秒自动执行**（不用按键）
- ⏹ 想打断/停止，随时按 `Esc`
- 🌐 全程本地处理，无云账号、无订阅、数据不出电脑

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

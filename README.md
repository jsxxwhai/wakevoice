<div align="center">

# 🎙️ WakeVoice

**对着电脑说话，它就帮你干活。**

一个**完全本地、离线可用**的中文语音助手：说一句唤醒词它就答应，再用嘴说出指令它照做——全程不用碰键盘，数据不出你的电脑。

> 💬 Wake word → spoken command → done. 100% on-device · no cloud · no subscription · private by default

[![Release](https://img.shields.io/github/v/release/jsxxwhai/wakevoice?color=blue&label=Latest%20Release)](https://github.com/jsxxwhai/wakevoice/releases)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![CI](https://github.com/jsxxwhai/wakevoice/actions/workflows/ci.yml/badge.svg)](https://github.com/jsxxwhai/wakevoice/actions/workflows/ci.yml)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Stars](https://img.shields.io/github/stars/jsxxwhai/wakevoice?style=social&label=Star)](https://github.com/jsxxwhai/wakevoice)

</div>

> [!NOTE]
> 这个项目是**原创独立开发的桌面语音助手**，不包含、不模仿任何第三方品牌或受版权保护的内容。MIT 协议开源，可自由使用、修改与再分发。


<div align="center">

**10+ 内置技能 · 9 种语音情绪 · 可自定义唤醒词 · 本地中文语音模型 · 一键便携 EXE**

</div>

<img src="assets/og-card.png" alt="WakeVoice 社交卡片" width="100%"/>

## ⭐ 为什么值得你点 Star

- 🆓 **完全免费、完全开源**（MIT）：不锁功能、不收费、可商用。
- 🔒 **本地优先**：唤醒、识别、基础对话全部在本地跑，断网也能用，隐私不出门。
- 🎙️ **真的不用手**：自定义唤醒词，说完停顿自动执行，解放双手。
- ⚡ **即开即用**：便携 EXE 版免装 Python，双击就能用。
- 🧩 **能自己扩展**：丢一个 `.py` 文件进 `skills/` 就多一个技能。

> ⭐ **如果它对你有帮助，请给仓库点一个 Star** —— 你的支持是作者持续维护的最大动力。

## 🚀 用起来是什么感觉

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
- ⏹ 想打断/停止，随时按 `Esc`（可在配置里关闭）
- 🌐 全程本地处理，无云账号、无订阅、数据不出电脑

![WakeVoice 对话演示（动画）](assets/demo.gif)

---
## Download

This project ships as **two distributions** — pick whichever fits your machine:

| Distribution | What you get | Requirements | Get it |
|---|---|---|---|
| **Source / green folder** | Full source + `安装并启动.bat` (auto-installs deps & downloads the speech model) | Windows 10/11 + Python 3.10+ | [wakevoice](https://github.com/jsxxwhai/wakevoice/releases) |
| **Portable EXE** | `WakeVoiceDesktop.exe` + bundled runtime; no Python needed. First launch downloads the speech model next to the exe. | Windows 10/11 (64-bit) | [wakevoice-portable](https://github.com/jsxxwhai/wakevoice-portable/releases) |

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

[MIT](LICENSE) © WakeVoice Contributors

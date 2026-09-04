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


<div align="center">

*Speak to your computer and it gets things done — fully local, offline-first, no cloud.*

</div>
> [!NOTE]
> 这个项目是**原创独立开发的桌面语音助手**，不包含、不模仿任何第三方品牌或受版权保护的内容。MIT 协议开源，可自由使用、修改与再分发。


<div align="center">

**10+ 内置技能 · 9 种语音情绪 · 可自定义唤醒词 · 本地中文语音模型 · 一键便携 EXE**

</div>


<img src="assets/og-card.png" alt="WakeVoice social card" width="100%"/>

## Why it deserves a ⭐

- 🆓 **Free & open source (MIT)** — nothing is locked, nothing to pay, commercial use is welcome.
- 🔒 **100% local & private** — wake-word, speech-to-text and basic replies all run on your PC; works fully offline; your voice never leaves the machine.
- 🎙️ **Truly hands-free** — set any custom wake word, then just talk; it acts automatically after a short pause. No keyboard needed.
- ⚡ **Zero-setup portable EXE** — double-click to run; no Python install, no command line.
- 🧩 **Extend with one file** — drop a `.py` file into `skills/` and you have a new capability.

> ⭐ **If WakeVoice helps you, please star this repository** — your support is what keeps the project alive and improving.

> [!NOTE]
> 这个项目是**原创独立开发的桌面语音助手**，不包含、不模仿任何第三方品牌或受版权保护的内容。MIT 协议开源，可自由使用、修改与再分发。

<details>
<summary><b>中文版 · 为什么值得点 Star</b></summary>

- 🆓 **完全免费、完全开源**（MIT）：不锁功能、不收费、可商用。
- 🔒 **本地优先**：唤醒、识别、基础对话全部在本地跑，断网也能用，隐私不出门。
- 🎙️ **真的不用手**：自定义唤醒词，说完停顿自动执行，解放双手。
- ⚡ **即开即用**：便携 EXE 版免装 Python，双击就能用。
- 🧩 **能自己扩展**：丢一个 `.py` 文件进 `skills/` 就多一个技能。

</details>

## What it feels like

A short real session (wake word default “你好伙伴”):

```text
You: 你好伙伴                       → “wake word”
Bot: 我在。有什么吩咐？              → “I'm here. What can I do for you?”
You: 打开记事本                      → “open a text editor”
     (pause ~1.5 s — no key press)
Bot: 好的，已经打开记事本了。         → “Done, the editor is open.”
You: 现在几点了？                    → “what time is it?”
Bot: 现在是下午 3 点 24 分。          → “It's 3:24 PM.”
You: 拜拜                           → “bye”
Bot: 再见，有需要随时叫我。           → “Goodbye — call me anytime.”
```

- 🔉 Say the wake word (default “你好伙伴”) and it answers “我在”
- 🗣️ Then speak a command out loud — it **acts automatically after a ~1.5 s pause**
- ⏹ Press `Esc` at any time to interrupt or abort (configurable)
- 🌐 Fully local: no cloud account, no subscription, data never leaves your PC

![WakeVoice demo (animated)](assets/demo.gif)

---
## Download（下载安装）

This project ships as **two distributions** — pick whichever fits your machine:

| Distribution | What you get | Requirements | Get it |
|---|---|---|---|
| **Source / green folder** | Full source + `安装并启动.bat` (auto-installs deps & downloads the speech model) | Windows 10/11 + Python 3.10+ | [wakevoice](https://github.com/jsxxwhai/wakevoice/releases) |
| **Portable EXE** | `WakeVoiceDesktop.exe` + bundled runtime; no Python needed. First launch downloads the speech model next to the exe. | Windows 10/11 (64-bit) | [wakevoice-portable](https://github.com/jsxxwhai/wakevoice-portable/releases) |

> Both versions speak the same assistant (wake word “你好伙伴”), and both are fully open source. The portable EXE is built from this repository by `scripts/build_dist.py`.

## Features（功能特性）

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

## Quickstart（快速开始）

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

## Voice modes（语音模式）

- **Wake word** — say your configured wake word, the assistant answers, then
  you speak your command.
- **Hands-free** — after the wake response, speak and pause; the assistant
  finalizes after a silence gap (`voice.silence_seconds`).
- **Push-to-talk** — hold a key (default Space) while speaking, release to
  finalize (`voice.mode: push_to_talk`).
- **Stop key** — press `Esc` (configurable) at any time to interrupt speech or
  abort listening. Can be disabled via `voice.stop_enabled: false`.

## Safety（安全设计）

Screen-affecting system operations (locking the screen, minimizing all
windows) are **disabled by default**. To enable:

```yaml
safety:
  allow_screen_control: true
```

Runtime temp files (e.g. synthesized audio) are kept inside the project
workspace (`runtime_tmp/`) rather than the OS temp drive, and are capped and
cleaned automatically.

## Configuration（配置说明）

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

## Built-in skills（内置技能）

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

## Plugins（技能插件）

Drop a `.py` file into `skills/` that defines `register_skills(registry)`:

```python
from assistant.skills.base import Skill

def register_skills(registry):
    registry.register(Skill(
        name="hello", description="say hello",
        patterns=["你好插件"],
        handler=lambda p, c: "你好呀！"))
```

## Multi-agent（多智能体）

```python
from assistant.agents.hub import Agent, AgentHub, AgentContext

hub = AgentHub()
hub.register(Agent(name="coder", role="写代码", system_prompt="你是一个程序员"))
ctx = AgentContext()
print(hub.dispatch("coder", "帮我写个快速排序", ctx))
```

## Project layout（项目结构）

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

## Roadmap（路线图）

- [x] Custom wake word + multiple backends
- [x] Emotional speech synthesis
- [x] Multi-agent + LLM tool calling
- [x] Custom extension client
- [x] Plugin auto-discovery
- [x] Safety railings (opt-in screen control, project-local temp files)
- [ ] GUI configuration editor
- [ ] Wake-word training toolkit
- [ ] Broader platform support (macOS/Linux polish)

## Documentation（文档）

- [Architecture](docs/architecture.md)
- [Extending](docs/extending.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## License（开源协议）

[MIT](LICENSE) © WakeVoice Contributors

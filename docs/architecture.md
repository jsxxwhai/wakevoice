# WakeVoice 架构设计

## 设计目标

1. **低内存**：全模块懒加载；STT/唤醒词共享同一个 Vosk 模型；TTS 按需初始化。
2. **高度可定制**：唤醒词、语音、情绪、技能、Agent、MCP 全部通过配置或注册扩展。
3. **多 Agent**：Agent 是独立角色，可并发执行，可接入 LLM。
4. **可扩展**：技能、Agent、MCP 都是插件式，新增能力只需几行代码。

## 模块职责

| 模块 | 职责 |
|------|------|
| core/config | 分层配置（默认值 < 用户配置 < 环境变量） |
| core/llm | OpenAI 兼容 LLM 封装 + 情绪识别 |
| core/app | 顶层装配，懒加载各子系统 |
| skills/base | 技能基类 + 注册表 + 路由 |
| skills/* | 内置技能（打开应用、控制电脑） |
| agents/hub | Agent 注册与分发 |
| agents/llm_agent | LLM 驱动的 Agent（技能优先 + 情绪兜底） |
| connectors/client | MCP 客户端 |
| tts/engine | 情感 TTS（edge / pyttsx3） |
| stt/vosk_stt | Vosk 离线语音识别 |
| wake/keyword | 唤醒词检测（可自定义） |
| screen/reader | 截图 + OCR |

## 数据流

```text
麦克风 ──> 唤醒词检测 ──> 触发 ──> 免提说话（停顿自动结束）──> STT 识别
                │                                        │
                │                                        ▼
                │                                技能路由（本地，快）
                │                                        │
                │                           命中？ ──是──> 执行技能 ──> 结果
                │                                        │
                │                                       否
                │                                        ▼
                │                                LLM Agent（情绪 + 回复）
                │                                        │
                └────────────── 回复 ────────────────────┘
                                            │
                                            ▼
                                      TTS 朗读（带情绪）
```

## 内存策略

- 启动时只加载配置和技能注册表（~14 MiB）。
- Vosk 模型在首次 STT/唤醒调用时才加载（~173 MiB，STT 与唤醒共享）。
- TTS 引擎按需初始化，edge 走网络、pyttsx3 走本地 SAPI。
- 所有重依赖用 lazy import，不 import 不占内存。

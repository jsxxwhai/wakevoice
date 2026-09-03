# OpenVoice Desktop（便携 EXE 版）

无需安装 Python 的绿色便携语音助手。解压后双击
`OpenVoiceDesktop.exe` 即可使用：唤醒它 → 说指令 → 停顿后执行。

> 本仓库是**便携分发包**。源码、构建脚本与开发文档在
> [openvoice-desktop](https://github.com/jsxxwhai/openvoice-desktop)。
> 中文完整使用说明见同目录 `使用说明.txt`。

## 系统要求

- Windows 10 / 11（64 位）
- 麦克风
- 首次运行联网（自动下载约 42MB 中文语音模型，之后可离线）

## 快速开始

1. 下载本仓库最新 Release 里的 `OpenVoiceDesktop-portable-vX.zip`。
2. 解压到任意目录（建议路径不含中文/空格）。
3. 双击 `OpenVoiceDesktop.exe`。首次运行会自动下载语音模型并进入监听。
4. 说“你好伙伴”→ 它答“我在”→ 说出指令 → 停顿 1.5 秒自动执行。

## 常用指令

- “打开记事本 / 打开计算器 / 打开 example.com”
- “现在几点 / 今天星期几”
- “读一下屏幕”（可选 OCR）
- 按 `Esc` 可随时停止当前任务。

## 配置与常见问题

- 自定义唤醒词：编辑程序目录 `config/config.yaml` 的 `wake.word`。
- 接大模型让回答更聪明：在 `config/config.yaml` 的 `llm` 段配置 `base_url` / `api_key`
  （指向任意兼容 Chat Completions 的服务端点），或设置对应环境变量。
- 提示“Windows 已保护你的电脑”→ 点“更多信息”→“仍要运行”（未签名程序的正常提示）。

## 如何自己打包

便携版由源码仓库一条命令产出：

```bash
python scripts/build_dist.py --clean --portable --zip
```

## 开源许可

[MIT](LICENSE) © OpenVoice Desktop Contributors

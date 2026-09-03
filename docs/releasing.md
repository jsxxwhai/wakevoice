# 双仓库发布指南（GitHub 两版分发）

OpenVoice Desktop 按“最终用户拿到的形态”拆成 **两个独立 GitHub 仓库**：

| 仓库 | 内容 | 适用用户 | 如何运行 |
|---|---|---|---|
| `openvoice-desktop` | 完整源码 + 一键脚本 `安装并启动.bat` | 愿意/需要看源码、会装 Python 的用户 | 双击 `安装并启动.bat`，自动装依赖→下模型→启动 |
| `openvoice-desktop-portable` | EXE 便携版（`OpenVoiceDesktop.exe` + `_internal/`） | 不想装 Python 的普通用户 | 双击 `OpenVoiceDesktop.exe`，首次自动下模型 |

> 两个版本**同源**：便携 EXE 由源码仓库的 `scripts/build_dist.py` 构建，只是分发形态不同。
> 语音助手行为完全一致：唤醒词“你好伙伴”→应答“我在”→口语指令→停顿 1.5 秒执行 / ESC 停止。

---

## 一、前置条件（只做一次）

```bash
# 1. GitHub CLI 登录（需要你的账号，浏览器会弹出授权）
gh auth login

# 2. 确认登录状态
gh auth status

# 3. 创建两个仓库（公开或私有都可以）
gh repo create openvoice-desktop        --public --description "OpenVoice Desktop - green source version (double-click launcher)"      --source . --push
gh repo create openvoice-desktop-portable --public --description "OpenVoice Desktop - portable EXE version (no Python needed)"
```

> 若本地 git 想同时关联两个远程（源码仓库为主、便携仓库为辅），在源码根目录：
> ```bash
> git remote add origin   https://github.com/jsxxwhai/openvoice-desktop.git
> git remote add portable https://github.com/jsxxwhai/openvoice-desktop-portable.git
> ```

---

## 二、发布源码版（仓库 A：openvoice-desktop）

流程：改版本 → 打 tag → 推送 → CI（GitHub Actions）自动跑测试并建 Release。

```bash
# 1) 从源码产出“源码绿色版 + 便携 EXE + 便携 zip”（本机需要有 PyInstaller）
python scripts/build_dist.py --clean --source --portable --zip

# 2) 提交并推送
git add -A
git commit -m "feat: prepare v0.2.0 dual distributions"
git tag v0.2.0
git push origin main v0.2.0
```

Release 会自动创建于
`https://github.com/jsxxwhai/openvoice-desktop/releases/tag/v0.2.0`，
内容为 `sdist` + `wheel` + 便携 zip（若你在工作流里额外上传）。

---

## 三、发布便携版（仓库 B：openvoice-desktop-portable）

便携仓库只放“运行所需文件 + 说明”，不放源码与构建脚本：

```bash
# 1) 在源码仓库构建出便携 zip（含 EXE、运行库、说明、不含语音模型）
python scripts/build_dist.py --clean --portable --zip
#   产物: build_out/OpenVoiceDesktop-portable-v0.2.0.zip

# 2) 把 zip 里的内容展开到便携仓库工作目录（zip 顶层是 OpenVoiceDesktop-v0.2.0/）
#    提交如下文件即可：
#    OpenVoiceDesktop.exe / _internal/ / 使用说明.txt / README.md / LICENSE
```

便携仓库 `README.md` 应使用 `release_templates/README_portable.md` 模板，
并在仓库 Settings → GitHub Pages 里把发布说明放好。

---

## 四、每次更新发布（半自动）

修改 `CHANGELOG.md` → 用 `scripts/publish_github.py`（或手动打 tag）→ 推送 tag 即可。
便携仓库侧：重新构建 zip → 覆盖提交 → 推送。

---

## 五、验证

- 源码版：双击 `安装并启动.bat`，能听到“唤醒词已就绪…”。
- 便携版：双击 `OpenVoiceDesktop.exe --version` 输出版本号；运行后对“你好伙伴”应答“我在”。
- 两个仓库各自 Releases 页能看到对应资产。

详细打包参数见 `scripts/build_dist.py` 顶部注释。

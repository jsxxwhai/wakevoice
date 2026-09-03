"""Build distributable packages for OpenVoice Desktop.

Produces two end-user artifacts under build_out/:

  1. source/    - green / source folder: Python + start scripts.
                  Double-click 安装并启动.bat -> bootstrap auto-installs
                  deps, downloads the model, verifies, then runs the app.
                  Requires Python 3.10+ installed on the user's machine.

  2. portable/  - PyInstaller onedir bundle: a folder with
                  OpenVoiceDesktop.exe. No Python needed. First launch
                  auto-downloads the speech model next to the exe.

Run:
  python scripts/build_dist.py [--clean]
  python scripts/build_dist.py --source --portable
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build_out"
SPEC = ROOT / "packaging" / "OpenVoiceDesktop.spec"
DIST_APP = ROOT / "dist" / "OpenVoiceDesktop"
PORTABLE = OUT / "portable"
SOURCE = OUT / "source"


def _version() -> str:
    """Read the current package version (kept in sync with pyproject)."""
    src_init = ROOT / "src" / "assistant" / "__init__.py"
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', src_init.read_text(encoding="utf-8"))
    return m.group(1) if m else "0.0.0"


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(str(c) for c in cmd))
    subprocess.check_call(cmd, cwd=str(ROOT))


def clean() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except Exception:
        run([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build_portable() -> None:
    ensure_pyinstaller()
    if not SPEC.exists():
        print("[build] spec not found:", SPEC)
        raise SystemExit(1)
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(SPEC)])
    if not DIST_APP.exists():
        print("[build] PyInstaller did not produce dist/OpenVoiceDesktop")
        raise SystemExit(1)
    if PORTABLE.exists():
        shutil.rmtree(PORTABLE)
    shutil.copytree(DIST_APP, PORTABLE)
    _remove_model_tree(PORTABLE)
    _write_portable_readme(PORTABLE)
    print("[build] portable bundle ->", PORTABLE)


def build_source() -> None:
    if SOURCE.exists():
        shutil.rmtree(SOURCE)
    SOURCE.mkdir(parents=True)
    names = [
        "main.py", "安装并启动.bat", "start.bat", "start.ps1", "config",
        "skills", "examples", "LICENSE", "README.md",
        "pyproject.toml", "scripts", "src", "Makefile", "CHANGELOG.md",
        "CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md",
        "docs", "release_templates",
        ".gitattributes", ".gitignore",
    ]
    for name in names:
        src = ROOT / name
        if not src.exists():
            print("[build] warning: missing source item:", name)
            continue
        if src.is_dir():
            shutil.copytree(src, SOURCE / name, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", ".pytest_cache", "*.egg-info"))
        else:
            shutil.copy2(src, SOURCE / name)
    _write_source_readme(SOURCE)
    print("[build] source bundle ->", SOURCE)


def _write_readme(dst: Path, filename: str, text: str) -> None:
    (dst / filename).write_text(text, encoding="utf-8")


def _remove_model_tree(folder: Path) -> None:
    """The speech model is downloaded by the launcher on first run; keep the
    distributable small and the download logic testable by excluding the model."""
    for child in folder.iterdir():
        if child.name.startswith("vosk-model-") and child.is_dir():
            shutil.rmtree(child)
            print(f"[build] removed bundled model dir: {child}")


def make_portable_zip() -> Path:
    """Zip the portable EXE folder (OpenVoiceDesktop.exe + _internal)."""
    if not PORTABLE.exists():
        print("[build] portable bundle missing; run --portable first")
        raise SystemExit(1)
    _remove_model_tree(PORTABLE)
    version = _version()
    out_name = f"OpenVoiceDesktop-portable-v{version}.zip"
    out = OUT / out_name
    if out.exists():
        out.unlink()
    root_name = f"OpenVoiceDesktop-v{version}"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        base = PORTABLE
        for f in sorted(base.rglob("*")):
            if f.is_file():
                rel = Path(root_name) / f.relative_to(base)
                z.write(f, rel)
    print(f"[build] portable zip -> {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return out


def _write_portable_readme(dst: Path) -> None:
    _write_readme(dst, "使用说明.txt", _PORTABLE_README)


def _write_source_readme(dst: Path) -> None:
    _write_readme(dst, "使用说明.txt", _SOURCE_README)


_SOURCE_README = """OpenVoice Desktop - 绿色源码版使用说明
==============================================

【这是什么】
一个运行在你自己电脑上的中文语音助手：叫它“你好伙伴”，它答应一声，
然后你用嘴说命令（打开软件、报时、读屏幕、聊天等），它就照做。
本版本无需安装任何依赖 —— 所有依赖和语音模型都会在第一次启动时自动
下载配置完成。

【系统要求】
- Windows 10 / 11
- 已安装 Python 3.10 或更高版本（如果没有：https://www.python.org/downloads/）
  安装时务必勾选 “Add Python to PATH”
- 电脑有麦克风
- 第一次运行需要联网（下载约 42MB 中文语音模型）

【使用方法 - 只需两步】
1. 把整个文件夹解压到任意位置（建议路径不要包含中文/空格）。
2. 双击  安装并启动.bat
   它会自动：检查 Python -> 安装依赖库 -> 下载语音模型 -> 验证环境 -> 启动助手。
   全过程只需一次，之后再启动都是“秒开”，直接进入语音助手。

【怎么跟它说话】
- 启动后先等它说话：唤醒词已就绪，叫我“你好伙伴”吧。
- 对它说“你好伙伴”，它会回答“我在。”。
- 然后直接说你要它做的事，说完停顿 1.5 秒，它就开始执行。
- 想让当前任务停下来：按 ESC 键。
- 想结束对话：对它说“再见 / 拜拜 / 退出”。

【可以试试的指令】
- “打开记事本” / “打开计算器”
- “现在几点”
- “今天星期几”
- “读一下屏幕”（需要先装中文 OCR，可选）
- 其它日常问题（没配大模型时用内置知识回答）

【常见问题】
Q: 双击后一闪而过？
A: 请确认已安装 Python 3.10+ 并勾选 Add Python to PATH，然后再双击。
   或右键“安装并启动.bat”选“编辑”，查看提示。
Q: 提示麦克风权限？
A: 允许即可；若之前拒绝过，请到 系统设置->隐私->麦克风 打开本程序权限。
Q: 想自定义唤醒词？
A: 用记事本打开 config/config.yaml（可复制 config.example.yaml 生成），
   修改 wake.word 为任意词，比如“小爱同学”。

【高级（可选）】
想接入大模型让回答更聪明：设置环境变量 OPENAI_API_KEY，或在
config/config.yaml 的 llm 段填入 base_url / key（支持 OpenAI 兼容接口，
如 DeepSeek、Ollama 等）。没有密钥也能正常使用本地技能。
"""


_PORTABLE_README = """OpenVoice Desktop - 便携版（EXE）使用说明
==============================================

【这是什么】
一个不需要安装 Python 的绿色便携语音助手。整个程序就在这个文件夹里，
把它放到哪里都能用，双击 EXE 就能跑。
中文语音模型（约 42MB）会在你第一次双击时自动下载到本文件夹，以后
可离线使用，也可以在其它电脑上把这个文件夹整个拷走继续用。

【系统要求】
- Windows 10 / 11（64 位）
- 电脑有麦克风
- 第一次运行需要联网（下载约 42MB 中文语音模型）

【使用方法 - 只需两步】
1. 把整个文件夹解压到任意位置（建议路径不要包含中文/空格）。
2. 双击  OpenVoiceDesktop.exe
   第一次运行会先自动下载语音模型（显示进度），完成后自动进入语音助手。

【怎么跟它说话】
- 启动后等它提示：唤醒词已就绪，叫我“你好伙伴”吧。
- 对它说“你好伙伴”，它会回答“我在。”。
- 然后直接说你要它做的事，说完停顿 1.5 秒，它就开始执行。
- 想让当前任务停下来：按 ESC 键。
- 想结束对话：对它说“再见 / 拜拜 / 退出”。

【可以试试的指令】
- “打开记事本” / “打开计算器”
- “现在几点” / “今天星期几”
- “读一下屏幕”（需要先装中文 OCR，可选）
- 其它日常问题

【常见问题】
Q: 双击 EXE 后提示“Windows 已保护你的电脑”？
A: 这是未签名程序的正常提示。点“更多信息”->“仍要运行”即可。
Q: 杀毒软件误报？
A: PyInstaller 打包的程序偶尔会被误报。添加信任即可；本程序完全开源。
Q: 提示麦克风权限？
A: 允许即可；若之前拒绝过，请到 系统设置->隐私->麦克风 打开本程序权限。
Q: 想自定义唤醒词？
A: 用记事本打开本文件夹里的 config/config.yaml，修改 wake.word 即可。

【高级（可选）】
想接入大模型让回答更聪明：设置系统环境变量 OPENAI_API_KEY，或在
config/config.yaml 的 llm 段填入 base_url / key（支持 OpenAI 兼容接口）。
没有密钥也能正常使用本地技能。
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Build OpenVoice Desktop distributions.")
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--portable", action="store_true")
    ap.add_argument("--source", action="store_true")
    ap.add_argument("--zip", action="store_true",
                    help="also produce OpenVoiceDesktop-portable-vX.zip from the portable folder")
    args = ap.parse_args()
    if args.clean:
        clean()
    if args.portable:
        build_portable()
    if args.source:
        build_source()
    if not args.portable and not args.source:
        build_source()
        build_portable()
    if args.zip or (args.portable and not args.source):
        make_portable_zip()
    elif args.zip and args.source and not args.portable:
        print("[build] --zip requires the portable bundle; run --portable --zip")
        return 1
    print("[build] done. artifacts under", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

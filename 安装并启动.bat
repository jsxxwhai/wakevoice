@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

title OpenVoice Desktop - 自动安装并启动

echo ============================================================
echo   欢迎使用 OpenVoice Desktop 中文语音助手
echo   本程序会自动完成以下步骤（只需一次，之后启动秒开）：
echo    1. 检查 Python 环境
echo    2. 安装所需依赖库
echo    3. 下载中文语音识别模型（约 42MB，需联网）
echo    4. 验证环境后自动启动
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo [错误] 未检测到 Python。
    echo 请先安装 Python 3.10 或更高版本，下载地址：
    echo   https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"，然后重新双击本文件。
    echo.
    pause
    exit /b 1
)

echo [1/4] 检查 Python 版本...
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 (
    echo.
    echo [错误] Python 版本过低，请安装 Python 3.10 或更高版本后重试。
    echo.
    pause
    exit /b 1
)
echo        OK

echo [2/4] 安装/检查依赖库（首次需要联网，请稍候）...
python scripts\bootstrap.py
if errorlevel 1 (
    echo.
    echo [错误] 依赖安装或模型下载未完成，请检查网络后重新双击本文件。
    echo.
    pause
    exit /b 1
)

echo [3/4] 验证环境...
echo        OK

echo [4/4] 正在启动语音助手...
echo.
echo   - 唤醒词：你好伙伴
echo   - 说完话停顿 1.5 秒自动执行
echo   - 随时按 ESC 可打断/停止
echo   - 退出：关闭本窗口
echo.
echo   请允许程序使用麦克风（若弹出系统提示请选择允许）。
echo.
python main.py --wake
echo.
echo 助手已退出。
pause
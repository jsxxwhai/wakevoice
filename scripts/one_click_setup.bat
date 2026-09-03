@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0\.."

title WakeVoice - 一键安装与启动

echo ============================================================
echo   WakeVoice 中文语音助手
echo   一键自动配置：检测 Python - 安装依赖 - 下载模型 - 启动
echo ============================================================
echo.

rem ---- 1) 检查 Python ----
where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没有检测到 Python。
    echo 请先到 https://www.python.org/downloads/ 下载并安装 Python 3.10 或更高版本。
    echo 安装时务必勾选 "Add Python to PATH"，然后重新双击本文件。
    echo.
    pause
    exit /b 1
)

rem ---- 2) 自动安装依赖 + 下载模型 + 自检（幂等，以后再次运行会秒过）----
echo [1/2] 正在检查并配置运行环境，首次运行可能需要几分钟，请耐心等待...
echo       （需要联网下载约 42MB 的中文语音模型，仅首次需要）
echo.
python scripts\bootstrap.py
if errorlevel 1 (
    echo.
    echo [错误] 环境配置未完成，请根据上面的提示检查网络或 Python 后重试。
    echo.
    pause
    exit /b 1
)

echo.
echo [2/2] 环境就绪，正在启动语音助手...
echo       唤醒词：你好伙伴    退出程序：关闭本窗口或按 Ctrl+C
echo       注意：请允许程序使用麦克风，否则无法语音输入。
echo.
python main.py --wake
if errorlevel 1 (
    echo.
    echo [提示] 助手已退出（可按 Ctrl+C 停止）。
)
echo.
pause
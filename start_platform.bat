@echo off
chcp 65001 >nul 2>&1
title Relics Platform

cd /d "%~dp0"

:: ── 检测 Python ──────────────────────────────────────
if exist "%~dp0python\python.exe" (
    set "PYTHON=%~dp0python\python.exe"
    set "PATH=%~dp0python;%~dp0python\Scripts;%PATH%"
    echo [OK] 使用内嵌 Python
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [错误] 未找到 Python。请先运行 setup.bat。
        pause
        exit /b 1
    )
    set "PYTHON=python"
    echo [OK] 使用系统 Python
)

:: ── 检查 config.yaml ─────────────────────────────────
if not exist "config.yaml" (
    echo [错误] 未找到 config.yaml，请先双击 setup.bat 初始化。
    pause
    exit /b 1
)

:: ── 检查依赖 ─────────────────────────────────────────
%PYTHON% -c "import yaml, fastapi, uvicorn" >nul 2>&1
if errorlevel 1 (
    echo [安装] 正在安装依赖...
    %PYTHON% -m pip install -r platform\webgis\requirements.txt -q
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请检查网络连接。
        pause
        exit /b 1
    )
)

:: ── 启动服务（host/port 从 config.yaml 读取，浏览器由 serve.py 自动打开） ──
set "PYTHONIOENCODING=utf-8"
%PYTHON% platform\webgis\serve.py

echo.
echo [停止] 服务已关闭。
pause

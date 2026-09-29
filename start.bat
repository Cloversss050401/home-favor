@echo off
chcp 65001 >nul
title HomeFlavor AI Recipe - One-Click Start
cd /d "%~dp0"

rem Locate uv: PATH first, then common install dirs, then known local dir.
set "UV_CMD="
for /f "delims=" %%I in ('where uv 2^>nul') do set "UV_CMD=%%I"
if not defined UV_CMD if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_CMD=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV_CMD if exist "%LOCALAPPDATA%\uv\uv.exe" set "UV_CMD=%LOCALAPPDATA%\uv\uv.exe"
if not defined UV_CMD if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UV_CMD=%LOCALAPPDATA%\Programs\uv\uv.exe"
if not defined UV_CMD if exist "D:\development\uv-x86_64-pc-windows-msvc\uv.exe" set "UV_CMD=D:\development\uv-x86_64-pc-windows-msvc\uv.exe"

if not defined UV_CMD (
    echo [ERROR] uv not found.
    echo        Install uv: powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    echo        Or add your uv.exe folder to PATH.
    pause
    exit /b 1
)

echo [INFO] Using uv: %UV_CMD%
"%UV_CMD%" run python scripts\dev_launcher.py
if errorlevel 1 (
    echo.
    echo [Failed] Launch aborted. See log above.
    pause
)

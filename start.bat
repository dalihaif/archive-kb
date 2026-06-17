@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
title 档案政策监控与知识库平台 - 启动器

:: ===============================================================
::  档案政策监控与知识库平台 - 一键启动脚本
::  适用于: Windows 10 / 11
::  用法:   双击 start.bat 即可（首次运行会自动安装环境）
:: ===============================================================

set "PROJECT_DIR=%~dp0"
set "PORT=5050"

:: ── 检查项目文件 ────────────────────────────────────────────────
if not exist "%PROJECT_DIR%app.py" (
    echo.
    echo  [错误] 未找到 app.py，请确保 start.bat 位于 archive-kb 项目目录下。
    echo         当前目录: %PROJECT_DIR%
    echo.
    pause
    exit /b 1
)

:: ── 第1步: 检查 Python 环境 ────────────────────────────────────
set "PYTHON_EXE="
set "PYPORTABLE=%PROJECT_DIR%pyportable"

:: 1a: 检查便携 Python (之前安装的)
if exist "%PYPORTABLE%\python.exe" (
    set "PYTHON_EXE=%PYPORTABLE%\python.exe"
    goto :check_deps
)

:: 1b: 检查系统 Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=python"
        echo.
        echo  [OK] 检测到系统 Python
        goto :check_deps
    )
)

:: 1c: 检查 py 启动器
where py >nul 2>&1
if %errorlevel% equ 0 (
    py -3 -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=py -3"
        echo.
        echo  [OK] 检测到 py 启动器
        goto :check_deps
    )
)

:: ── 第2步: 下载便携 Python ─────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║       未检测到 Python，正在自动安装运行环境...             ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

set "PYTHON_VER=3.12"
set "PYTHON_ZIP=python-3.12.10-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.10/%PYTHON_ZIP%"

mkdir "%PYPORTABLE%" 2>nul

echo  [1/4] 正在下载 Python %PYTHON_VER% 便携版...
echo         (约 12MB，请耐心等待)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYPORTABLE%\%PYTHON_ZIP%' -UseBasicParsing; Write-Host 'OK' } catch { Write-Host \"FAIL: $_\"; exit 1 }"
if errorlevel 1 (
    echo.
    echo  [错误] Python 下载失败，请检查网络连接后重试。
    echo         可手动下载后放入 pyportable 目录。
    echo.
    pause
    exit /b 1
)
if not exist "%PYPORTABLE%\%PYTHON_ZIP%" (
    echo  [错误] 下载文件不存在，请重试。
    pause
    exit /b 1
)
echo         下载完成!
echo.

:: ── 第3步: 解压 Python ─────────────────────────────────────────
echo  [2/4] 正在解压 Python...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%PYPORTABLE%\%PYTHON_ZIP%' -DestinationPath '%PYPORTABLE%' -Force"
if errorlevel 1 (
    echo  [错误] Python 解压失败。
    pause
    exit /b 1
)
del "%PYPORTABLE%\%PYTHON_ZIP%" 2>nul

:: 修改 ._pth 文件，启用 site-packages (pip 必需)
for %%f in ("%PYPORTABLE%\python*._pth") do (
    powershell -NoProfile -Command ^
        "(Get-Content '%%f') -replace '^#import site','import site' | Set-Content '%%f'"
)
echo         解压完成!
echo.

:: ── 第4步: 安装 pip ────────────────────────────────────────────
echo  [3/4] 正在安装 pip 包管理器...
set "PIP_URL=https://bootstrap.pypa.io/get-pip.py"
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%PIP_URL%' -OutFile '%PYPORTABLE%\get-pip.py' -UseBasicParsing; Write-Host 'OK' } catch { Write-Host \"FAIL: $_\"; exit 1 }"
if errorlevel 1 (
    echo  [错误] pip 下载失败。
    pause
    exit /b 1
)
"%PYPORTABLE%\python.exe" "%PYPORTABLE%\get-pip.py" --no-warn-script-location >nul 2>&1
if errorlevel 1 (
    echo  [错误] pip 安装失败。
    pause
    exit /b 1
)
del "%PYPORTABLE%\get-pip.py" 2>nul
echo         pip 安装完成!
echo.

set "PYTHON_EXE=%PYPORTABLE%\python.exe"

:: ── 第5步: 安装依赖 ────────────────────────────────────────────
:check_deps
echo  [4/4] 正在检查并安装项目依赖...
echo.

:: 核心依赖检查
"%PYTHON_EXE%" -c "import flask; import sqlalchemy; import bs4; import requests; import apscheduler; import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo         正在安装核心依赖 (首次运行需要 3~5 分钟)...
    echo         请勿关闭此窗口，请耐心等待...
    echo.
    if exist "%PROJECT_DIR%requirements.txt" (
        "%PYTHON_EXE%" -m pip install --quiet --no-warn-script-location -r "%PROJECT_DIR%requirements.txt"
    ) else (
        "%PYTHON_EXE%" -m pip install --quiet --no-warn-script-location ^
            flask flask-sqlalchemy beautifulsoup4 lxml requests ^
            apscheduler openpyxl
    )
    if errorlevel 1 (
        echo  [警告] 部分依赖安装失败，尝试继续启动...
    ) else (
        echo.
        echo         核心依赖安装完成!
    )
) else (
    echo         核心依赖已满足。
)

:: 可选依赖: Scrapling (较大，安装失败不影响核心功能)
"%PYTHON_EXE%" -c "import scrapling" >nul 2>&1
if errorlevel 1 (
    echo.
    echo         正在安装 Scrapling (智能网页抓取引擎)...
    "%PYTHON_EXE%" -m pip install --quiet --no-warn-script-location scrapling 2>nul
    if errorlevel 1 (
        echo         [提示] Scrapling 安装失败，将使用备用抓取引擎，不影响正常使用。
    ) else (
        echo         Scrapling 安装完成!
    )
)

echo.
echo         依赖检查完成!
echo.

:: ── 第6步: 启动服务器 ──────────────────────────────────────────
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║            档案政策监控与知识库平台 启动中...              ║
echo  ╠══════════════════════════════════════════════════════════╣
echo  ║                                                            ║
echo  ║   本地访问:   http://127.0.0.1:%PORT%                     ║
echo  ║   管理后台:   http://127.0.0.1:%PORT%/admin               ║
echo  ║                                                            ║
echo  ║   [提示] 后台无需登录，直接进入即可使用                     ║
echo  ║                                                            ║
echo  ║   关闭方式:   按 Ctrl+C 或直接关闭此窗口                   ║
echo  ║                                                            ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: 延迟3秒后自动打开浏览器
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:%PORT%"

:: 启动 Flask 应用
cd /d "%PROJECT_DIR%"
"%PYTHON_EXE%" app.py

:: 如果 Flask 退出了
echo.
echo  [提示] 服务器已停止。
echo         如果这是意外退出，请检查上方错误信息。
echo.
pause

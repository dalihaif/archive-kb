@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "SETUP_PY=%SCRIPT_DIR%setup.py"

echo ==============================================
echo  档案政策监控与知识库平台
echo  正在启动...
echo ==============================================
echo.

REM 查找 Python
set "PY="
if exist "%SCRIPT_DIR%pyportable\python.exe" (
    set "PY=%SCRIPT_DIR%pyportable\python.exe"
    goto :run
)
where python >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=python"
    goto :run
)
where py >nul 2>&1
if !errorlevel! equ 0 (
    set "PY=py -3"
    goto :run
)

echo [错误] 未找到 Python，将自动下载安装...
echo.
"%SCRIPT_DIR%setup.py"

:run
if defined PY (
    cd /d "%SCRIPT_DIR%"
    "%PY%" "%SETUP_PY%"
)

if errorlevel 1 (
    echo.
    echo [错误] 启动失败，请检查上方错误信息。
    pause
)

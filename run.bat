@echo off
rem Double-click launcher for kolobot.
rem
rem Messages here are deliberately ASCII. A console opened by a double click
rem runs at the OEM code page (437 on this machine), which has no Cyrillic, and
rem "chcp 65001" inside a .bat makes cmd lose its place in the file and try to
rem execute fragments of later lines.
rem
rem The venv is called directly instead of via Activate.ps1: no ExecutionPolicy
rem involved, and "No module named 'aiogram'" cannot happen.

rem Run from this file's folder, so .env and the relative paths inside it resolve
rem the same way they do when the bot is started from a terminal here.
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [ERROR] No virtual environment found at:
    echo         %CD%\.venv
    echo.
    echo Create it and install the dependencies:
    echo     python -m venv .venv
    echo     .venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    goto :end
)

if not exist ".env" (
    echo [ERROR] No .env file found in:
    echo         %CD%
    echo.
    echo Copy the template and fill in your tokens:
    echo     copy .env.example .env
    echo.
    goto :end
)

echo Starting kolobot. Close this window or press Ctrl+C to stop it.
echo.

"%PY%" -m kolobot
set "CODE=%ERRORLEVEL%"

echo.
if "%CODE%"=="0" (
    echo kolobot stopped.
) else (
    echo kolobot exited with error code %CODE%.
)

:end
echo.
pause

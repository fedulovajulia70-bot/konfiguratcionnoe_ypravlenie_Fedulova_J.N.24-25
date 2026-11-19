@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON (
    "%PYTHON%" src\main.py %*
) else (
    python src\main.py %*
)
exit /b %errorlevel%

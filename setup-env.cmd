@echo off
setlocal
rem Purpose: create or synchronize the root Python 3.12 virtual environment.
rem Input: installed uv and optional --no-pause.
rem Output: ignored .venv and process exit code; existing .env is untouched.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-env.ps1"
set "SUPPORT_EXIT_CODE=%ERRORLEVEL%"
if not "%SUPPORT_EXIT_CODE%"=="0" echo Environment setup failed. See the preceding error.
if /I not "%~1"=="--no-pause" pause
exit /b %SUPPORT_EXIT_CODE%

@echo off
setlocal
rem Purpose: start and verify the local Docker application.
rem Input: optional --no-pause; local .env is created only when missing.
rem Output: local URL and exit code; services keep running after exit.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-local.ps1"
set "SUPPORT_EXIT_CODE=%ERRORLEVEL%"
if not "%SUPPORT_EXIT_CODE%"=="0" echo Startup failed. See the preceding error.
if /I not "%~1"=="--no-pause" pause
exit /b %SUPPORT_EXIT_CODE%

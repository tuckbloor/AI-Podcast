@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Podcast Outreach AI Installer
if not exist "%~dp0tools\podcast_install.py" goto :incomplete
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
  if not errorlevel 1 (
    py -3 "%~dp0tools\podcast_install.py" %*
    goto :result
  )
)
where python >nul 2>nul
if errorlevel 1 goto :missing
python -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>nul
if errorlevel 1 goto :missing
python "%~dp0tools\podcast_install.py" %*
:result
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
exit /b %CODE%
:incomplete
echo ERROR: Full Podcast Outreach AI source ZIP required. Extract every file and retry.
pause
exit /b 1
:missing
echo ERROR: Python 3.11 or newer is required: https://www.python.org/downloads/windows/
pause
exit /b 1

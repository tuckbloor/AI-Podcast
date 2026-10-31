@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto check
 echo Creating Python environment...
 where py >nul 2>nul
 if not errorlevel 1 (
    py -3.14 --version >nul 2>nul
    if not errorlevel 1 (py -3.14 -m venv .venv) else (py -3 -m venv .venv)
 ) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Python 3.11+ is required. Install Python from python.org and reopen this window.
        exit /b 1
    )
    python -m venv .venv
 )
 if errorlevel 1 (
    echo ERROR: Unable to create the virtual environment.
    exit /b 1
 )
:check
".venv\Scripts\python.exe" -c "import streamlit, requests, bs4" >nul 2>nul
if not errorlevel 1 exit /b 0
 echo Installing project dependencies (first launch)...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed. Check your internet connection and Python installation.
    exit /b 1
)
exit /b 0

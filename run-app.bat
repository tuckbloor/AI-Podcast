@echo off
cd /d "%~dp0"
call "%~dp0prepare-env.bat"
if errorlevel 1 (
    echo.
    echo Application setup failed. Review the error above.
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m streamlit run "%~dp0app.py"
if errorlevel 1 pause

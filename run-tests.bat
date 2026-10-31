@echo off
cd /d "%~dp0"
call "%~dp0prepare-env.bat"
if errorlevel 1 (
    pause
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 (
    pause
    exit /b 1
)
echo All tests passed.

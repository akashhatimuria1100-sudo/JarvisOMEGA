@echo off
cd /d "%~dp0"
echo Starting JARVIS OMEGA V8...
python main.py
if errorlevel 1 (
    echo.
    echo ERROR: JARVIS failed to start!
    echo Make sure you ran install.bat first.
    pause
)
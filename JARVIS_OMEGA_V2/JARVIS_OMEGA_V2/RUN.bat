@echo off
title JARVIS OMEGA V2
color 0B
echo.
echo  ⚡ Starting JARVIS OMEGA V2...
echo.
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo  ❌ JARVIS failed to start.
    echo  Run SETUP.bat first if you haven't.
    pause
)

@echo off
title J.A.R.V.I.S OMEGA V4
color 0B
cd /d "%~dp0"
echo Starting JARVIS OMEGA V4...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: JARVIS failed to start.
    echo Run SETUP.bat first to install dependencies.
    pause
)

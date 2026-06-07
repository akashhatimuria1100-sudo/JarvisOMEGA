@echo off
title JARVIS OMEGA V4 — Setup
color 0B
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║     J.A.R.V.I.S OMEGA V4 — SETUP                    ║
echo  ║     Pure pip only. No winget. No ffmpeg.             ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

echo [1/5] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [2/5] Installing core dependencies...
pip install PyQt6 groq pyttsx3 sounddevice soundfile numpy requests beautifulsoup4 lxml psutil httpx pyautogui pillow

echo.
echo [3/5] Installing speech recognition...
pip install SpeechRecognition

echo.
echo [4/5] Installing edge-tts (optional neural voice)...
pip install edge-tts

echo.
echo [5/5] Done! All dependencies installed.
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  Setup complete! Now:                                ║
echo  ║  1. Edit config\settings.json with your Groq API key ║
echo  ║     OR click Settings inside JARVIS after launch     ║
echo  ║  2. Run: python main.py                              ║
echo  ║     OR double-click: RUN.bat                         ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause

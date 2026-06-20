@echo off
REM ═══════════════════════════════════════════════════════════════════════════
REM  JARVIS OMEGA V8 — One-Click Installer for Windows
REM  Double-click this file to install everything automatically
REM ═══════════════════════════════════════════════════════════════════════════

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       JARVIS OMEGA V8 INSTALLER          ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.11+ from https://python.org
    echo Make sure to check "Add to PATH" during install.
    pause
    exit /b 1
)

echo [OK] Python found
python --version

echo.
echo [STEP 1/4] Upgrading pip...
python -m pip install --upgrade pip --quiet

echo.
echo [STEP 2/4] Installing core packages...
pip install PyQt6 requests edge-tts pyttsx3 pygame playsound pyautogui pygetwindow Pillow duckduckgo-search --quiet

echo.
echo [STEP 3/4] Installing speech recognition...
pip install SpeechRecognition --quiet

echo.
echo [STEP 4/4] Installing PyAudio (mic support)...
pip install pipwin --quiet
pipwin install pyaudio
if %errorlevel% neq 0 (
    echo.
    echo [WARN] PyAudio install via pipwin failed.
    echo Trying alternative method...
    pip install pyaudio --quiet
    if %errorlevel% neq 0 (
        echo.
        echo [WARN] Could not install PyAudio automatically.
        echo Voice INPUT will not work until PyAudio is installed.
        echo Manual install: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
        echo Or run: conda install pyaudio
        echo.
        echo TTS (voice OUTPUT) and chat will still work without PyAudio.
    )
)

echo.
echo ═══════════════════════════════════════════════════════
echo  Installation complete!
echo.
echo  NEXT STEPS:
echo  1. Open .env file and add your API keys
echo     (or get free keys from the websites listed in .env)
echo  2. Run JARVIS:  double-click  run.bat
echo     or type:     python main.py
echo ═══════════════════════════════════════════════════════
echo.
pause

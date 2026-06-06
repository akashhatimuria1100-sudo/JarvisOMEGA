@echo off
title JARVIS OMEGA V2 — Setup
color 0B
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       JARVIS OMEGA V2 — SETUP                       ║
echo  ╚══════════════════════════════════════════════════════╝
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python not found! Download from python.org
    pause
    exit /b
)
echo  ✅ Python found

:: Upgrade pip
echo.
echo  Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install requirements
echo.
echo  Installing packages (this may take 5-10 minutes)...
echo  Note: PyTorch may be large (~2GB)
echo.
pip install -r requirements.txt

:: Check for PyAudio (tricky on Windows)
python -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ⚠️  PyAudio install may have failed.
    echo  If voice doesn't work, manually install:
    echo  1. Go to: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
    echo  2. Download the .whl for your Python version
    echo  3. Run: pip install [downloaded-file].whl
)

:: Check Tesseract
where tesseract >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ⚠️  Tesseract OCR not found (optional - for screen reading).
    echo  Download: https://github.com/UB-Mannheim/tesseract/wiki
)

echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║  ✅ Setup complete!                                  ║
echo  ║                                                      ║
echo  ║  NEXT STEP: Add your FREE Groq API key:             ║
echo  ║  1. Go to: console.groq.com                         ║
echo  ║  2. Create a free account                           ║
echo  ║  3. Copy your API key                               ║
echo  ║  4. Open: config\settings.json                      ║
echo  ║  5. Paste into: "groq_api_key": "YOUR_KEY_HERE"    ║
echo  ║                                                      ║
echo  ║  Then run: RUN.bat                                  ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
pause

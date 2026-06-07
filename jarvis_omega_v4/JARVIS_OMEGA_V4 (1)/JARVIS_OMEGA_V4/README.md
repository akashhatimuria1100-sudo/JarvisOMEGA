# ⚡ J.A.R.V.I.S OMEGA V3

**Iron Man HUD AI Assistant — Fully Fixed for Python 3.14**

---

## 🚀 Quick Start

1. **Run `SETUP.bat`** — installs all Python dependencies
2. **Get a FREE Groq API key** at [console.groq.com](https://console.groq.com)
3. **Run `RUN.bat`** to launch JARVIS
4. Click **⚙ Settings** → paste your Groq API key → Save
5. Restart JARVIS — you're online!

---

## ✅ All Bugs Fixed (V2 → V3)

### GUI
- ✅ **Iron Man HUD interface** — matches the Rainmeter-style reference screenshot
- ✅ **Arc Reactor animation** — full multi-ring design matching the physical reactor photo (hexagonal core, copper coils, rotating segments)
- ✅ **Output panel is now much larger** — messages show fully, no clipping
- ✅ **Images display inline** in the chat panel (generated images appear right in the conversation)
- ✅ **Code panel** shows code + output with syntax highlighting

### Listening / Voice
- ✅ **180s = SESSION timeout**, NOT per-command wait time
- ✅ Each command: AI listens → detects speech end via silence (1.8s) → transcribes → responds
- ✅ Never hangs waiting 180 seconds for a single command
- ✅ "Stop" / "stop listening" ends the session early
- ✅ Wake word "Jarvis listen" starts the 3-minute voice session

### Speaking
- ✅ **No pygame** (no Python 3.14 wheel) → uses `sounddevice + soundfile` instead
- ✅ **No playsound** (broken on 3.14) → proper audio playback chain
- ✅ edge-tts async loop fixed (no more event loop leaks)
- ✅ pyttsx3 as reliable offline fallback

### App Control
- ✅ App opening works (Chrome, Notepad, VSCode, etc.)
- ✅ Screen reading returns word positions so AI can click
- ✅ `find_on_screen` finds UI elements by text label
- ✅ pywinauto integration for native Windows app control

### AI Features
- ✅ **Groq API error handling** — clear messages if key is missing/wrong
- ✅ **Self-improvement works** — AI can `install_skill` to add new packages
- ✅ **Image generation** — Pollinations.ai (free, no key needed) + saves locally
- ✅ **File saving** — files go to `Documents/JARVIS/` folder
- ✅ **Python code** runs with correct Python (`sys.executable`)

---

## 🐍 Python 3.14 Package Changes

| Old (broken on 3.14) | New (works on 3.14) |
|----------------------|---------------------|
| `pyaudio`            | `sounddevice + soundfile` |
| `pygame`             | `sounddevice + soundfile` |
| `playsound`          | `subprocess` (PowerShell/mpg123) |

---

## 📦 Dependencies

```
PyQt6>=6.6.0          — GUI
groq>=0.9.0           — AI brain (free at console.groq.com)
edge-tts>=6.1.9       — Neural TTS (Microsoft voices)
pyttsx3>=2.90         — Offline TTS fallback
sounddevice>=0.4.6    — Audio playback + recording (replaces pygame+pyaudio)
soundfile>=0.12.1     — WAV/MP3 file reading
speechrecognition     — Fallback STT via Google
requests              — Web search, image generation
beautifulsoup4        — Web scraping
pillow                — Screenshots, image handling
pyautogui             — Mouse/keyboard control
psutil                — System stats
numpy                 — Audio processing

# Optional:
openai-whisper        — Offline STT (needs torch)
pytesseract           — OCR screen reading
pywinauto             — Windows app UI control
selenium              — Web browser automation
```

---

## 🗂 Project Structure

```
JARVIS_OMEGA_V3/
├── main.py                  ← Entry point (run this)
├── RUN.bat                  ← Windows launcher
├── SETUP.bat                ← Installer
├── requirements.txt         ← All dependencies
├── config/
│   └── settings.json        ← API key, voice settings
├── core/
│   ├── brain.py             ← AI brain + Groq integration
│   ├── memory.py            ← Conversation memory
│   ├── context.py           ← Context analysis
│   └── self_improve.py      ← Self-improvement engine
├── gui/
│   └── main_window.py       ← Iron Man HUD GUI
├── speech/
│   ├── listener.py          ← Voice input (sounddevice)
│   ├── speaker.py           ← TTS output (edge-tts)
│   └── wake_detector.py     ← Wake word detection
├── tools/
│   ├── tool_manager.py      ← Tool dispatcher
│   ├── app_controller.py    ← App control (pywinauto/selenium)
│   ├── vision_tools.py      ← Screen reading + OCR
│   ├── image_tools.py       ← Image generation (Pollinations.ai)
│   ├── web_tools.py         ← Web search (DuckDuckGo)
│   ├── code_tools.py        ← Code generation
│   └── system_tools.py      ← System info
└── data/
    ├── screenshots/         ← Saved screenshots
    ├── images/              ← Generated images
    └── projects/            ← Created projects
```

---

## 🔑 Getting Your Free Groq API Key

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free, no credit card needed)
3. Go to **API Keys** → **Create API Key**
4. Copy the key
5. In JARVIS: click **⚙ Settings** → paste in **Groq API Key** → **Save**
6. Restart JARVIS

---

## 🎤 Voice Commands

| Say                      | What happens                           |
|--------------------------|----------------------------------------|
| "Jarvis listen"          | Starts 3-minute voice session          |
| "Stop" / "Stop listening"| Ends voice session                     |
| "Open Chrome"            | Opens Chrome browser                   |
| "Search [topic]"         | Web search via DuckDuckGo              |
| "Generate image of X"    | Creates image using Pollinations.ai    |
| "Create a snake game"    | Generates + saves Python game          |
| "Take a screenshot"      | Captures screen + reads content        |
| "Show system info"       | CPU, RAM, battery, network status      |
| "Remember that X is Y"   | Saves to persistent memory             |

---

*JARVIS OMEGA V3 — Built for Python 3.14 | Iron Man Interface | Groq AI*

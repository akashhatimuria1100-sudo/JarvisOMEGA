# ⚡ JARVIS OMEGA — AI Operating System

> *"Just A Rather Very Intelligent System"*  
> Iron Man-inspired, fully autonomous AI assistant for Windows/Linux/Mac  
> **100% FREE — Powered by Groq API (free tier)**

---

## 🚀 Quick Start

### Step 1 — Get FREE Groq API Key
1. Go to **[console.groq.com](https://console.groq.com)**
2. Sign up (no credit card needed)
3. Click **API Keys → Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 2 — Install
```bash
# Windows
SETUP.bat

# Linux / Mac
pip install -r requirements.txt
```

### Step 3 — Configure
Open `config/settings.json` and add your key:
```json
{
  "groq_api_key": "gsk_your_key_here",
  "user_name": "YourName"
}
```

### Step 4 — Run
```bash
# Windows
RUN.bat

# Linux / Mac
python main.py
```

---

## 🧠 Features

### Multi-Agent Architecture
| Agent | Role |
|-------|------|
| 🗺 PlannerAgent | Breaks complex goals into steps |
| 🔍 ResearchAgent | Web search & knowledge gathering |
| 💻 CodingAgent | Code generation & project creation |
| 👁 VisionAgent | Screen reading & OCR |
| 🤖 AutomationAgent | Computer control (mouse/keyboard) |
| 🧠 MemoryAgent | Persistent memory & learning |
| 🔧 DeviceAgent | Arduino & hardware control |
| 🛡 SecurityAgent | Validates dangerous actions |

### 🎤 Voice System
- **Always-on wake word**: Say "JARVIS" to activate
- **Double Ctrl** hotkey to toggle listening mode
- Multi-language: English, Hindi, Hinglish
- Auto-detects language and responds in kind
- 3-minute active listening window

### 🔮 Neural Orb
- Animated desktop overlay (always on top)
- States: Idle / Listening / Thinking / Speaking / Executing / Error
- Draggable, dockable
- Right-click context menu

### 💻 Computer Control
- Open/close any app
- Mouse control (move, click, drag, scroll)
- Keyboard typing and hotkeys
- File and folder management
- Screenshot and screen reading

### 🤖 Autonomous Project Creation
Say: *"Create a snake game in Python"*  
JARVIS will:
1. Plan the project structure
2. Generate all source files
3. Create README with instructions
4. Save to `data/projects/`

### ⚡ Arduino & Hardware
- Auto-detect Arduino/ESP32/ESP8266
- Generate and upload firmware
- Monitor serial data
- Generate circuit diagrams
- Generate OpenSCAD 3D print files

### 🌐 Web Research
- Free DuckDuckGo search (no API key)
- Background silent research
- Auto-learns from search results
- Displays results in output panel

### 🖼 Image Generation
- **Free**: Pollinations.ai (no API key)
- **Optional**: Stability AI / DALL-E (if you have keys)
- Styles: photorealistic, anime, 3D, concept art, dark
- Auto-saves to `data/images/`

---

## 📁 Project Structure

```
JARVIS_OMEGA/
├── main.py                  ← Entry point
├── config/
│   └── settings.json        ← Your configuration
├── core/
│   ├── brain.py             ← Multi-agent AI brain
│   ├── memory.py            ← Persistent memory engine
│   ├── context.py           ← Intent & language detection
│   └── self_improve.py      ← Background learning engine
├── gui/
│   └── main_window.py       ← Revolutionary UI + Neural Orb
├── speech/
│   ├── speaker.py           ← TTS (pyttsx3 + gTTS)
│   ├── listener.py          ← STT (Google free)
│   └── wake_detector.py     ← Wake word + hotkey
├── tools/
│   ├── tool_manager.py      ← Action dispatcher
│   ├── web_tools.py         ← DuckDuckGo search (free)
│   ├── code_tools.py        ← Autonomous project creation
│   ├── vision_tools.py      ← Screen reading + OCR
│   ├── system_tools.py      ← System info & control
│   ├── arduino_tools.py     ← Hardware integration
│   └── image_tools.py       ← Image generation (free)
├── data/
│   ├── projects/            ← Generated projects
│   ├── images/              ← Generated images
│   ├── screenshots/         ← Screen captures
│   └── knowledge.json       ← Learned knowledge base
├── requirements.txt
├── SETUP.bat               ← Windows setup
└── RUN.bat                 ← Windows launcher
```

---

## 🗣 Example Commands

```
"Open VS Code and create a Python calculator"
"Search latest news about AI 2025"
"Take a screenshot and describe what you see"
"Create a snake game with pygame"
"What's my system status?"
"Create an Arduino LED blink program"
"Generate an image of a futuristic city"
"Open Spotify"
"Remember: I prefer dark mode"
"Search DuckDuckGo for Python tutorials"
"Create a website for my portfolio"
"Type Hello World in notepad"
```

---

## ⚙ Configuration Options

| Key | Default | Description |
|-----|---------|-------------|
| `groq_api_key` | `""` | FREE key from console.groq.com |
| `user_name` | `"Akash"` | Your name for greeting |
| `ai_name` | `"JARVIS"` | AI's name |
| `groq_model` | `llama-3.3-70b-versatile` | Best free model |
| `wake_word` | `"jarvis"` | Wake word |
| `tts_rate` | `180` | Speech speed (words/min) |
| `overlay_enabled` | `true` | Floating orb on/off |
| `self_improve` | `true` | Background learning |
| `temperature` | `0.7` | AI creativity (0-1) |

---

## 🆓 Free AI Models (Groq)

| Model | Quality | Speed |
|-------|---------|-------|
| `llama-3.3-70b-versatile` | ⭐⭐⭐⭐⭐ | Fast |
| `mixtral-8x7b-32768` | ⭐⭐⭐⭐ | Fast |
| `llama3-70b-8192` | ⭐⭐⭐⭐ | Fast |
| `gemma2-9b-it` | ⭐⭐⭐ | Very Fast |
| `llama3-8b-8192` | ⭐⭐ | Fastest |

---

## 🛡 Security

- All dangerous system commands are validated before execution
- No CAPTCHAs are bypassed (JARVIS will ask you to complete them)
- Destructive operations require confirmation
- Code runs in isolated subprocess
- No data is sent to third parties (except Groq API for AI responses)

---

## 🔧 Optional Enhancements

### Better OCR
```bash
# Install Tesseract
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# Linux:
sudo apt install tesseract-ocr
pip install pytesseract
```

### Arduino Upload
```bash
# Install arduino-cli
# https://arduino.github.io/arduino-cli/
```

### Background Removal
```bash
pip install rembg
```

---

## 📝 License
Free for personal use. Built with ❤️ by JARVIS OMEGA.

---

*"The suit's the least of it."* — Tony Stark

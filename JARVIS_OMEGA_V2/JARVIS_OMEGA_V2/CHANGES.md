# JARVIS OMEGA V2 — What's Fixed & What's New

## 🔴 Critical Bug Fixes

### 1. Voice Recognition (speech/listener.py) — REBUILT
- **Before:** Fixed 8-second blocking record, always sent silence to Google STT
- **After:** Real-time pyaudio stream + silero-VAD detects exactly when you start/stop speaking
- **Before:** Google STT (network-dependent, ~3s latency, often fails)
- **After:** Whisper (local, offline, <1s latency, works without internet)
- **Improvement:** Hindi/Hinglish/English all work offline now

### 2. Text-to-Speech (speech/speaker.py) — REBUILT
- **Before:** pyttsx3 (robotic Windows voice), 500-char hard limit cut responses mid-word
- **After:** edge-tts with Microsoft Neural voices (en-US-GuyNeural, en-IN-NeerjaNeural etc.)
- **Before:** Blocking TTS froze the UI
- **After:** Async streaming — speech starts in ~200ms, non-blocking
- **Before:** Long replies were silently truncated
- **After:** No length limit — full responses spoken, sentence-chunked for fast start

### 3. GUI Text Truncation (gui/main_window.py) — FIXED
- **Before:** MessageBubble used QLabel with fixed size — long text was cut off silently
- **After:** Uses QTextBrowser — all text fully shown, scrollable, word-wrapped
- **Before:** AI responses were truncated in display
- **After:** Full responses always visible, auto-scrolls to bottom

### 4. GUI Close Kills JARVIS (gui/main_window.py) — FIXED
- **Before:** Clicking X called stop() on all systems and quit the process
- **After:** Clicking X hides the window to system tray — JARVIS keeps running
- **New:** Right-click tray icon → Show / Listen / Quit
- **New:** Double-click tray icon → Show main window

### 5. App Control — Can't Control After Opening (tools/app_controller.py) — NEW MODULE
- **Before:** tool_manager only used subprocess.Popen to open apps, nothing after
- **After:** WindowsAppController uses pywinauto UI Automation to:
  - Attach to any running window by name or title
  - Read the full UI element tree (buttons, fields, menus)
  - Click by element name: `click_element("Save")` not `click_at(x=842, y=312)`
  - Type into fields by label: `type_in_element("Search", "hello world")`
  - Read element text, take window screenshots

### 6. Web App Control — NEW (tools/app_controller.py)
- **New:** WebAppController uses Selenium to control Chrome/Edge
- Click web buttons by their text: `click_web_element("Submit")`
- Type in web fields by placeholder: `type_in_web("Search", placeholder="Search...")`
- Read page content, navigate URLs
- Auto-installs ChromeDriver/EdgeDriver via webdriver-manager

### 7. GUI Clutter — Removed Skill Panels
- **Before:** Skills panel, options panel always visible, making GUI complex
- **After:** Minimal interface — just orb + chat + input bar
- **New:** All settings accessible via ⚙ button or right-click orb menu

### 8. VSCode Minimize — NEW
- **Before:** Running code left JARVIS window on top of VSCode
- **After:** When run_code executes, main window auto-minimizes
- Window restores automatically after code execution finishes

### 9. Self-Improvement Engine (core/self_improve.py) — MAJOR UPGRADE
- **Before:** Only scraped DuckDuckGo snippets and stored as memory text
- **After:** Full autonomous improvement pipeline:
  - `CodeAnalyzer`: AST-parses own codebase, finds stub functions and TODOs
  - `FeatureWriter`: asks LLM to write new skill code
  - `SandboxTester`: tests code in isolated subprocess (with safety checks)
  - `AutoIntegrator`: saves skill to skills/installed/, registers in registry
  - Hot-reload: new skills work immediately, no restart needed
  - `GitCommitter`: auto-commits improvements with descriptive messages

### 10. Orb Drag-and-Drop
- Orb already draggable — position saved to settings on release
- Click orb toggles main window (show/hide)
- Right-click orb = context menu with all main actions

---

## 📦 New Packages Required

```
openai-whisper     # Offline speech recognition
pyaudio            # Real-time audio streaming
torch + torchaudio # Silero-VAD for voice detection
edge-tts           # Microsoft Neural TTS (free)
pygame             # Audio playback
pywinauto          # Windows UI Automation
selenium           # Web browser control
webdriver-manager  # Auto ChromeDriver install
gitpython          # Git integration for self-improve
```

---

## 🚀 Quick Start

1. Run `SETUP.bat`
2. Get free API key at `console.groq.com`
3. Add key to `config/settings.json` → `groq_api_key`
4. Run `RUN.bat`

---

## 💬 New Commands You Can Try

- `"Open Notepad and type Hello World"` — real app control
- `"Go to youtube.com and search for Python tutorials"` — web control
- `"Create a snake game and run it"` — code with VSCode minimize
- `"Write a new skill for controlling Spotify"` — self-improvement
- `"What's running on my computer?"` — app discovery

# ⚡ JARVIS OMEGA V8

> Your personal AI assistant — works with voice in **Hinglish**, controls your PC, and runs offline too.

---

## 🔧 WHAT WAS FIXED IN V8

| # | Problem | Fix |
|---|---------|-----|
| 1 | **Apps not opening** | Rewrote `automation.py` with full Windows paths + `subprocess.Popen`. `os.system()` was silently failing. |
| 2 | **Web pages not opening** | Added `webbrowser.open()` call — was missing entirely. |
| 3 | **TTS not working** | Fixed Edge TTS async — now runs in its own thread with `asyncio.run()` so it never blocks. Added `pyttsx3` offline fallback. |
| 4 | **Chat panel showing Hindi (Devanagari)** | Added `hindi_to_hinglish()` conversion. System prompt now strictly instructs AI to use Roman-script Hinglish only. |
| 5 | **Voice recognising wrong words** | Added Whisper (via Groq) as primary STT — much better accuracy for Indian English + Hindi mixed speech. Added `_CORRECTIONS` map for common mishears. Multi-language fallback: `hi-en → en-IN → en-US`. |
| 6 | **API keys showing as wrong/not working** | Added format validators per provider (`gsk_` for Groq, `csk-` for Cerebras, `nvapi-` for NVIDIA, `AIza` for Google, UUID format for SambaNova/OpenRouter). Keys are validated on startup with clear error messages. |
| 7 | **OpenRouter key truncated** | OpenRouter key was cut short in `.env`. Added UUID validation that skips truncated keys and prints a clear message to get a full key. |
| 8 | **No offline mode** | Added full Ollama support. Install Ollama + `ollama pull llama3.2`, toggle "Offline (Ollama)" in the UI. |
| 9 | **CMD output not showing results** | Fixed action output panel — shows ✅/❌ for every action with result message. |
| 10 | **Google API key wrong format** | Google key must start with `AIza`. Validator added; key is skipped with clear message if format is wrong. |

---

## 🚀 QUICK START

### Step 1 — Install
```
Double-click:  install.bat
```

### Step 2 — Add API Keys
Open `.env` and paste your keys. All providers below have **free tiers**:

| Provider | Free Key From | Used For |
|----------|--------------|---------|
| **Groq** | https://console.groq.com | Fastest chat + Whisper STT |
| **Cerebras** | https://cloud.cerebras.ai | Ultra-fast responses (~0.3s) |
| **SambaNova** | https://cloud.sambanova.ai | Long context chat |
| **OpenRouter** | https://openrouter.ai | Free fallback models |
| **NVIDIA NIM** | https://build.nvidia.com | Fallback |
| **Google** | https://aistudio.google.com | Gemini fallback |
| **Ollama** | https://ollama.ai | 100% offline, no internet |

> ✅ You only need **ONE** key to use JARVIS. Groq is recommended (free + fast + Whisper STT).

### Step 3 — Run
```
Double-click:  run.bat
```

---

## 🎙️ VOICE COMMANDS (Hinglish — works with mix of Hindi + English)

| Say this | What happens |
|----------|-------------|
| `Chrome kholo` / `Open Chrome` | Opens Google Chrome |
| `YouTube pe songs dhundo` / `Search YouTube for songs` | Opens YouTube search |
| `Google pe weather search karo` | Google search opens |
| `Notepad kholo` | Opens Notepad |
| `Screenshot lo` | Takes screenshot → saves to `data/screenshots/` |
| `Volume badhao` / `Volume up` | Increases system volume |
| `Mute karo` / `Mute` | Mutes/unmutes audio |
| `Spotify pe music bajao` | Opens Spotify |
| `Wikipedia pe Einstein dhundo` | Google search for Einstein |
| `Aaj ka time kya hai` | Tells current time |
| `Aaj ki date batao` | Tells today's date |

---

## 🔌 OFFLINE MODE (No Internet Needed)

1. Install Ollama: https://ollama.ai
2. Open terminal and run:
   ```
   ollama pull llama3.2
   ollama serve
   ```
3. In JARVIS, tick **"Offline (Ollama)"** checkbox in sidebar
4. JARVIS will now use your local Llama model — zero internet required

---

## 🗣️ HINGLISH MODE

JARVIS always responds in **Hinglish** — Hindi words written in English letters, the way Indians chat on WhatsApp.

**Example response:**
> "Sir, main abhi Chrome khol deta hoon. YouTube search bhi usi mein ho jayega."

- ✅ **Roman script** (English letters) — readable in chat panel
- ❌ **No Devanagari** (Hindi letters like क ख ग) — these are never shown
- The "Hinglish Display" toggle in the sidebar controls this

---

## 📁 PROJECT STRUCTURE

```
JARVIS_OMEGA_V8/
├── main.py                ← Entry point — loads settings, starts Qt app
├── .env                   ← YOUR API KEYS (never share this file)
├── .env.example           ← Template — copy to .env and fill in keys
├── requirements.txt       ← Python packages
├── install.bat            ← One-click installer (Windows)
├── run.bat                ← One-click launcher (Windows)
│
├── config/
│   └── settings.json      ← Voice, display, model settings
│
├── core/
│   └── brain.py           ← AI logic, API calls, action extraction, memory
│
├── speech/
│   ├── stt_engine.py      ← Voice recognition (Whisper + Google STT)
│   └── tts_engine.py      ← Text-to-speech (Edge TTS + pyttsx3 fallback)
│
├── gui/
│   └── main_window.py     ← Qt6 GUI — chat panel, mic button, settings
│
├── tools/
│   └── automation.py      ← PC control — open apps, browser, keyboard, etc.
│
└── data/
    ├── memory.db          ← Conversation history (SQLite)
    └── screenshots/       ← Screenshots saved here
```

---

## ⚠️ TROUBLESHOOTING

### "No API key working"
- Open `.env` — make sure keys don't have spaces or extra quotes
- Check the key format shown in the sidebar (green = OK, red = bad format)
- Get fresh keys from the websites listed above — old keys expire

### "Voice not recognising properly"
- Make sure microphone is set as default in Windows Sound settings
- Speak clearly, pause briefly before and after your command
- Try switching to English-only if Hinglish recognition is poor:
  Change `"stt_language": "hi-en"` to `"en-IN"` in `config/settings.json`
- With a Groq key, Whisper gives much better accuracy

### "TTS / Voice output not working"
- Run: `pip install edge-tts pygame` in terminal
- Check internet connection (Edge TTS needs internet)
- For offline TTS: `pip install pyttsx3` — works without internet

### "App not opening"
- Check if the app is installed in the standard location
- You can add custom paths in `tools/automation.py` under `_APPS`
- Try saying the exact app name: "Visual Studio Code kholo"

### "PyAudio install fails"
```
pip install pipwin
pipwin install pyaudio
```
If that fails, download wheel from:
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

---

## 🔑 API KEY FORMAT REFERENCE

| Provider | Key Format | Example start |
|----------|-----------|--------------|
| Groq | `gsk_...` | `gsk_fSyv0pmi...` |
| Cerebras | `csk-...` | `csk-mxj9w...` |
| SambaNova | UUID format | `6b0b355b-67b0-43c0-...` |
| OpenRouter | UUID format | `55b-67b0-...` ❌ (yours was truncated — get full key) |
| NVIDIA | `nvapi-...` | `nvapi-t8j1U2...` |
| Google | `AIza...` | `AIzaSy...` |

> **Your OpenRouter key appears truncated** — get a fresh full UUID from https://openrouter.ai/keys

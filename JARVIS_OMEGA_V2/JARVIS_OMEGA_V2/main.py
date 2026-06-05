"""
╔══════════════════════════════════════════════════════════════════╗
║          J.A.R.V.I.S  OMEGA  V2  AI  OPERATING  SYSTEM          ║
║          Just A Rather Very Intelligent System                    ║
║                                                                   ║
║  ✅ Whisper STT + Silero-VAD  (offline, fast, accurate)          ║
║  ✅ Microsoft Neural TTS      (Alexa-quality, FREE)              ║
║  ✅ Real App Control          (click by element name)            ║
║  ✅ Web App Control           (Selenium)                         ║
║  ✅ Clean GUI                 (no clutter, draggable orb)        ║
║  ✅ Hides to tray on close    (stays running)                    ║
║  ✅ Self-Improving Engine V2  (AST + LLM + git commit)           ║
║  ✅ Full text display         (no truncation ever)               ║
║  ✅ VSCode auto-minimize      (when running code)                ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import logging
from pathlib import Path

os.chdir(Path(__file__).resolve().parent)
sys.path.insert(0, str(Path(__file__).resolve().parent))

# ── Create required directories ──────────────────────────────────────────────
for folder in ["data", "data/images", "data/projects", "data/screenshots",
               "data/recordings", "config", "logs", "temp", "skills/installed",
               "agents", "tools"]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/jarvis.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("JARVIS.MAIN")

# ── Default settings ─────────────────────────────────────────────────────────
DEFAULT_SETTINGS = {
    "groq_api_key":             "",
    "ai_name":                  "JARVIS",
    "user_name":                "Sir",
    "groq_model":               "llama-3.3-70b-versatile",
    "tts_rate":                 175,
    "tts_voice_index":          0,
    "tts_voice":                "en-US-GuyNeural",
    "tts_edge_rate":            "+0%",
    "tts_edge_pitch":           "+0Hz",
    "wake_word":                "jarvis",
    "wake_hotkey":              "ctrl+ctrl",
    "listening_timeout":        180,
    "overlay_enabled":          True,
    "overlay_position":         [None, None],
    "theme":                    "omega_dark",
    "temperature":              0.7,
    "max_tokens":               2048,
    "offline_mode":             False,
    "self_improve":             True,
    "autonomous_improve":       False,
    "self_improve_interval_hours": 6,
    "screen_monitor":           True,
    "auto_startup":             False,
    "security_level":           "standard",
    "arduino_port":             "auto",
    "fast_mode":                False,
    "multi_agent":              True,
    "cinematic_mode":           True,
    "whisper_model":            "base",
    "languages":                ["en-IN", "hi-IN", "en-US"],
}

settings_path = Path("config/settings.json")
settings = DEFAULT_SETTINGS.copy()

if settings_path.exists():
    try:
        loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        settings.update(loaded)
        logger.info("Settings loaded.")
    except Exception as exc:
        logger.warning("Could not load settings: %s", exc)
else:
    settings_path.write_text(json.dumps(DEFAULT_SETTINGS, indent=2), encoding="utf-8")
    logger.info("Created default settings.")

settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

# ── API key warning ───────────────────────────────────────────────────────────
api_key = settings.get("groq_api_key", "").strip()
if not api_key:
    print("\n" + "═" * 60)
    print("  ⚠️  GROQ API KEY NOT FOUND")
    print("  Get your FREE key at: console.groq.com")
    print("  Add it to: config/settings.json → groq_api_key")
    print("  Running in limited offline mode.")
    print("═" * 60 + "\n")

# ── Data defaults ────────────────────────────────────────────────────────────
data_defaults = {
    "data/knowledge.json":        {"entries": []},
    "data/conversation_log.json": [],
    "data/persona_memory.json": {
        "name": settings.get("user_name", "Sir"),
        "preferences": {},
        "frequent_topics": {},
        "speaking_style": "professional_casual",
        "languages_used": ["en"],
        "learned_facts": [],
        "projects": [],
        "corrections": [],
    },
    "data/task_history.json":     {"tasks": []},
    "data/skills_registry.json":  {"installed": [], "available": []},
    "data/digital_twin.json":     {"apps": [], "files": [], "devices": [], "hardware": []},
}
for fp, default in data_defaults.items():
    p = Path(fp)
    if not p.exists():
        p.write_text(json.dumps(default, indent=2), encoding="utf-8")


def launch_gui():
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from gui.main_window import JarvisOmegaWindow

        app = QApplication(sys.argv)
        app.setStyle("Fusion")

        # AA_UseHighDpiPixmaps was removed in PyQt6 6.4+ — skip safely
        try:
            app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
        except AttributeError:
            pass  # Not needed in modern PyQt6 — HiDPI is always on

        # Keep app running even when window is hidden (tray mode)
        app.setQuitOnLastWindowClosed(False)

        # ── First-run API key wizard ──────────────────────────────────────
        if not settings.get("groq_api_key", "").strip():
            _show_api_key_wizard(app, settings)

        window = JarvisOmegaWindow(settings)
        window.show()

        logger.info("JARVIS OMEGA V2 GUI launched.")
        sys.exit(app.exec())

    except ImportError as exc:
        logger.error("Missing dependency: %s", exc)
        print(f"\n❌ Missing: {exc}")
        print("Run: pip install -r requirements.txt")
        run_console()
    except Exception as exc:
        logger.error("GUI launch failed: %s", exc, exc_info=True)
        print(f"\n❌ Error: {exc}")
        run_console()


def _show_api_key_wizard(app, settings: dict):
    """Show a simple dialog to enter the Groq API key on first run."""
    try:
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel,
            QLineEdit, QPushButton, QFrame
        )
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont

        dlg = QDialog()
        dlg.setWindowTitle("JARVIS OMEGA V2 — Setup")
        dlg.setFixedSize(520, 300)
        dlg.setWindowFlags(
            dlg.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        dlg.setStyleSheet("""
            QDialog  { background: #020810; }
            QLabel   { color: #e0e8f0; }
            QLineEdit {
                background: #060f20; color: #e0e8f0;
                border: 1px solid #1a3a5c; border-radius: 6px;
                padding: 8px; font-size: 13px;
            }
            QPushButton {
                background: #1a4a8a; color: #e0e8f0;
                border: none; border-radius: 6px;
                padding: 9px 20px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #2255a0; }
            QPushButton#skip  { background: #0d2540; }
        """)

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("⚡ JARVIS OMEGA V2 — First Run")
        title.setStyleSheet("color:#00d4ff; font-size:16px; font-weight:bold;")
        layout.addWidget(title)

        sub = QLabel(
            "No Groq API key found. JARVIS needs this to think and speak.\n"
            "It's 100% FREE — no credit card needed."
        )
        sub.setStyleSheet("color:#6a8aaa; font-size:12px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        link = QLabel('<a href="https://console.groq.com" style="color:#00d4ff;">→ Get your free key at console.groq.com</a>')
        link.setOpenExternalLinks(True)
        link.setStyleSheet("font-size:12px;")
        layout.addWidget(link)

        key_field = QLineEdit()
        key_field.setPlaceholderText("Paste your Groq API key here…")
        key_field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(key_field)

        btn_row = QHBoxLayout()
        skip_btn = QPushButton("Skip for now")
        skip_btn.setObjectName("skip")
        save_btn = QPushButton("✅ Save & Launch")

        def _save():
            key = key_field.text().strip()
            if key:
                settings["groq_api_key"] = key
                settings_path.write_text(
                    json.dumps(settings, indent=2), encoding="utf-8"
                )
                logger.info("API key saved from wizard.")
            dlg.accept()

        save_btn.clicked.connect(_save)
        skip_btn.clicked.connect(dlg.reject)
        key_field.returnPressed.connect(_save)

        btn_row.addWidget(skip_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

        dlg.exec()
    except Exception as exc:
        logger.warning("API key wizard failed: %s", exc)


def run_console():
    print("\n" + "═" * 60)
    print("  JARVIS OMEGA V2 — Console Mode")
    print("═" * 60)
    try:
        from core.brain import JarvisOmegaBrain
        brain = JarvisOmegaBrain(settings)
        print("  Type 'exit' to quit.\n")
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit", "bye"):
                print("JARVIS: Goodbye.")
                break
            if user_input:
                reply = brain.process(user_input)
                print(f"\nJARVIS: {reply}\n")
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as exc:
        print(f"\nError: {exc}")
        print("Install deps: pip install -r requirements.txt")


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  ⚡ JARVIS OMEGA V2 — AI Operating System")
    print("  Voice • App Control • Self-Improving • Always-On")
    print("═" * 60 + "\n")
    logger.info("Starting JARVIS OMEGA V2...")
    launch_gui()

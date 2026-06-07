"""
main.py — JARVIS OMEGA V3 Entry Point
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run: python main.py
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

# Add project root to path so all imports work
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from PyQt6.QtWidgets import QApplication
from gui.main_window import JarvisOmegaWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS OMEGA V3")
    app.setQuitOnLastWindowClosed(False)

    # Load or create settings
    settings_path = BASE / "config/settings.json"
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            settings = {}
    else:
        settings = {}

    # Default values
    defaults = {
        "user_name":      "Sir",
        "ai_name":        "JARVIS",
        "wake_word":      "jarvis",
        "groq_api_key":   "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",
        "groq_model":     "llama-3.3-70b-versatile",
        "whisper_model":  "base",
        "tts_voice":      "en-IN-NeerjaNeural",
        "tts_edge_rate":  "+5%",
        "tts_edge_pitch": "-5Hz",
        "tts_rate":       170,
        "temperature":    0.7,
        "max_tokens":     2048,
        "overlay_enabled": True,
        "self_improve":   True,
        "languages":      ["en-IN", "en-US"],
    }
    for k, v in defaults.items():
        settings.setdefault(k, v)

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    window = JarvisOmegaWindow(settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

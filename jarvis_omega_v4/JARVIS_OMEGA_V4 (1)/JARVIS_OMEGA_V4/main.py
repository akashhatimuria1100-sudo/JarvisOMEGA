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
    has_key = bool(settings.get("groq_api_key", "").strip())
    defaults = {
        "user_name":           "Sir",
        "ai_name":             "JARVIS",
        "wake_word":           "jarvis",
        "groq_api_key":        "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",
        "google_api_key":      "AQ.Ab8RN6INc7AW8EcTQXjJVuB8NhdbUZJDIORJwipQGhxL68X2JQ",
        "openrouter_api_key":  "",
        "nvidia_api_key":      "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",
        "sambanova_api_key":   "6b0b355b-67b0-43c0-ab81-85ea67952bab",
        "cerebras_api_key":    "csk-mxj9wffr2xfp5d8wpm5xye9pfh689vxmfe5y8yrykj2r82er",
        "groq_model":          "llama-3.3-70b-versatile",
        "whisper_model":       "base",
        "tts_voice":           "en-US-GuyNeural",
        "tts_edge_rate":       "+5%",
        "tts_edge_pitch":      "-5Hz",
        "tts_rate":            220,
        "temperature":         0.7,
        "max_tokens":          2048,
        "overlay_enabled":     True,
        "self_improve":        True,
        "languages":           ["hi-IN", "en-IN", "en-US"],
        "hinglish_mode":       True,
        "use_local_llm":       True,   # always load local as backup, cloud providers are primary
    }

    # Force Hinglish on for legacy configs that never had the key
    if "hinglish_mode" not in settings:
        settings["hinglish_mode"] = True

    for k, v in defaults.items():
        settings.setdefault(k, v)

    if settings.get("hinglish_mode", True):
        settings["languages"] = ["hi-IN", "en-IN", "en-US"]

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    window = JarvisOmegaWindow(settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
main.py — JARVIS OMEGA V2 Entry Point
"""

import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)

from PyQt6.QtWidgets import QApplication
from gui.main_window import JarvisOmegaWindow


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Load settings
    base = Path(__file__).resolve().parent
    settings_path = base / "config/settings.json"

    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        settings = {
            "user_name": "Sir",
            "ai_name": "JARVIS",
            "wake_word": "jarvis",
            "overlay_enabled": True,
        }
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

    window = JarvisOmegaWindow(settings)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
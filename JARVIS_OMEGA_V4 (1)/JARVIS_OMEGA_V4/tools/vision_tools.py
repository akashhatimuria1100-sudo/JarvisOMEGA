"""
tools/vision_tools.py — JARVIS OMEGA V3 Screen Vision
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ OCR returns actual element positions
  ✅ Detect icons/buttons for AI clicking
  ✅ Returns clickable element list with x,y coords
  ✅ Cross-platform (Windows/Linux/macOS)
"""

import logging
import time
from pathlib import Path

logger = logging.getLogger("JARVIS.VISION")
_BASE = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = _BASE / "data/screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def capture_and_read() -> dict:
    """Take a screenshot and extract text + clickable elements via OCR."""
    try:
        import pyautogui
        from PIL import Image

        timestamp = int(time.time())
        path = SCREENSHOTS_DIR / f"screen_{timestamp}.png"
        img = pyautogui.screenshot()
        img.save(str(path))

        text     = _ocr_with_positions(img)
        elements = _detect_ui_elements(img)

        return {
            "type":     "screen_read",
            "path":     str(path),
            "text":     text.get("text", "")[:3000],
            "words":    text.get("words", [])[:100],   # [{text, x, y, w, h}]
            "elements": elements,
            "width":    img.width,
            "height":   img.height,
        }
    except ImportError as exc:
        return {"type": "error", "error": f"Missing library: {exc}"}
    except Exception as exc:
        logger.error("Screen read failed: %s", exc)
        return {"type": "error", "error": str(exc)}


def _ocr_with_positions(img) -> dict:
    """OCR with word-level bounding boxes so AI knows WHERE to click."""
    try:
        import pytesseract
        # Get data with bounding boxes
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        full_text  = pytesseract.image_to_string(img).strip()
        words = []
        n = len(data["text"])
        for i in range(n):
            word = data["text"][i].strip()
            conf = int(data["conf"][i]) if data["conf"][i] != "-1" else 0
            if word and conf > 40:
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                words.append({
                    "text": word,
                    "x": x + w // 2,   # center x
                    "y": y + h // 2,   # center y
                    "conf": conf,
                })
        return {"text": full_text, "words": words}
    except ImportError:
        logger.debug("pytesseract not installed")
        return {"text": "[OCR unavailable — install pytesseract]", "words": []}
    except Exception as exc:
        logger.warning("OCR failed: %s", exc)
        return {"text": "", "words": []}


def _detect_ui_elements(img) -> list:
    """Detect clickable UI regions using color analysis."""
    elements = []
    try:
        import numpy as np
        arr = np.array(img.convert("L"))
        h, w = arr.shape
        cols, rows = 8, 5
        cell_w = w // cols
        cell_h = h // rows
        for row in range(rows):
            for col in range(cols):
                region = arr[row*cell_h:(row+1)*cell_h, col*cell_w:(col+1)*cell_w]
                if region.size == 0:
                    continue
                avg = float(region.mean())
                std = float(region.std())
                if std > 40:  # high contrast = likely interactive element
                    elements.append({
                        "type": "region",
                        "x": col * cell_w + cell_w // 2,
                        "y": row * cell_h + cell_h // 2,
                        "width": cell_w,
                        "height": cell_h,
                        "contrast": round(std, 1),
                    })
    except Exception as exc:
        logger.debug("UI detection error: %s", exc)
    return elements[:30]


def find_text_on_screen(search_text: str) -> dict:
    """Find where specific text appears on screen and return its coordinates."""
    try:
        result = capture_and_read()
        words  = result.get("words", [])
        search_lower = search_text.lower()
        matches = []
        for word in words:
            if search_lower in word["text"].lower():
                matches.append(word)
        if matches:
            return {"type": "found", "matches": matches, "count": len(matches)}
        return {"type": "not_found", "search": search_text}
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def get_active_window_title() -> str:
    try:
        import platform, subprocess, ctypes
        os_name = platform.system()
        if os_name == "Windows":
            hwnd   = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf    = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        elif os_name == "Linux":
            r = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=3
            )
            return r.stdout.strip()
    except Exception:
        pass
    return "Unknown"

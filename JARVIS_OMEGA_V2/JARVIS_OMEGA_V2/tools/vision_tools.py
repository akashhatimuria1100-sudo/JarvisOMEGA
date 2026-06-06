"""
tools/vision_tools.py — Screen capture, OCR, UI understanding
Free using pytesseract + PIL (no paid API needed)
"""

import logging
from pathlib import Path
import time

logger = logging.getLogger("JARVIS.VISION")
_BASE = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = _BASE / "data/screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def capture_and_read() -> dict:
    """Take a screenshot and extract text via OCR."""
    try:
        import pyautogui
        from PIL import Image

        timestamp = int(time.time())
        path = SCREENSHOTS_DIR / f"screen_{timestamp}.png"

        # Capture screen
        img = pyautogui.screenshot()
        img.save(str(path))

        # OCR text extraction
        text = _ocr(img)

        # UI element detection
        elements = _detect_ui_elements(img)

        return {
            "type":     "screen_read",
            "path":     str(path),
            "text":     text[:3000],
            "elements": elements,
            "width":    img.width,
            "height":   img.height,
        }
    except ImportError as exc:
        return {"type": "error", "error": f"Missing library: {exc}"}
    except Exception as exc:
        logger.error("Screen read failed: %s", exc)
        return {"type": "error", "error": str(exc)}


def _ocr(img) -> str:
    """Extract text from image using pytesseract or fallback."""
    try:
        import pytesseract
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        logger.debug("pytesseract not installed — no OCR")
        return "[OCR unavailable — install pytesseract and Tesseract-OCR]"
    except Exception as exc:
        logger.warning("OCR failed: %s", exc)
        return ""


def _detect_ui_elements(img) -> list:
    """Detect basic UI regions using color/contrast analysis."""
    elements = []
    try:
        from PIL import ImageFilter, ImageOps
        import numpy as np

        # Convert to grayscale for analysis
        gray = img.convert("L")
        width, height = img.size

        # Simple region detection: scan for high-contrast areas (buttons/text areas)
        # Divide screen into 6x4 grid and check contrast
        cols, rows = 6, 4
        cell_w = width // cols
        cell_h = height // rows

        for row in range(rows):
            for col in range(cols):
                left   = col * cell_w
                top    = row * cell_h
                right  = left + cell_w
                bottom = top + cell_h
                region = gray.crop((left, top, right, bottom))
                pixels = list(region.getdata())
                if not pixels:
                    continue
                avg = sum(pixels) / len(pixels)
                variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)
                if variance > 2000:  # High contrast = likely interactive element
                    elements.append({
                        "type": "interactive_region",
                        "x": left + cell_w // 2,
                        "y": top + cell_h // 2,
                        "width": cell_w,
                        "height": cell_h,
                        "contrast": round(variance, 1),
                    })
    except Exception as exc:
        logger.debug("UI detection failed: %s", exc)
    return elements[:20]


def capture_region(x: int, y: int, w: int, h: int) -> dict:
    """Capture a specific screen region."""
    try:
        import pyautogui
        img = pyautogui.screenshot(region=(x, y, w, h))
        timestamp = int(time.time())
        path = SCREENSHOTS_DIR / f"region_{timestamp}.png"
        img.save(str(path))
        text = _ocr(img)
        return {"type": "region_captured", "path": str(path), "text": text}
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def find_on_screen(image_path: str) -> dict:
    """Find an image on screen and return its position."""
    try:
        import pyautogui
        loc = pyautogui.locateOnScreen(image_path, confidence=0.8)
        if loc:
            center = pyautogui.center(loc)
            return {"type": "found", "x": center.x, "y": center.y}
        return {"type": "not_found"}
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def get_active_window_title() -> str:
    """Get the title of the currently active window."""
    try:
        import subprocess, platform
        os_name = platform.system()
        if os_name == "Windows":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        elif os_name == "Linux":
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=3
            )
            return result.stdout.strip()
        return "Unknown"
    except Exception:
        return "Unknown"

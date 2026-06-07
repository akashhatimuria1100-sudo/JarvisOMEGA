"""
tools/vision_tools.py — JARVIS OMEGA V4 Screen Vision
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ OCR returns exact element positions with high confidence
  ✅ Better text grouping (words → phrases) for accurate click targets
  ✅ Icon/button detection via contrast analysis
  ✅ Cross-platform (Windows/Linux/macOS)
  ✅ Fuzzy text matching for finding elements even with OCR errors
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

        # Merge words into phrases for better click targets
        phrases = _merge_words_into_phrases(text.get("words", []))

        return {
            "type":     "screen_read",
            "path":     str(path),
            "text":     text.get("text", "")[:3000],
            "words":    text.get("words", [])[:100],
            "phrases":  phrases[:50],          # grouped text for easier clicking
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
            if word and conf > 30:
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                words.append({
                    "text": word,
                    "x": x + w // 2,   # center x
                    "y": y + h // 2,   # center y
                    "left": x,
                    "top": y,
                    "width": w,
                    "height": h,
                    "conf": conf,
                })
        return {"text": full_text, "words": words}
    except ImportError:
        logger.debug("pytesseract not installed")
        return {"text": "[OCR unavailable — install pytesseract]", "words": []}
    except Exception as exc:
        logger.warning("OCR failed: %s", exc)
        return {"text": "", "words": []}


def _merge_words_into_phrases(words: list, max_gap_x: int = 30, max_gap_y: int = 8) -> list:
    """
    Group OCR words that are close together into phrases.
    This gives the AI better click targets like 'Search' or 'Sign in'.
    """
    if not words:
        return []
    # Sort by y then x
    sorted_words = sorted(words, key=lambda w: (w["y"], w["x"]))
    phrases = []
    current = [sorted_words[0]]

    for w in sorted_words[1:]:
        last = current[-1]
        # Same line (similar y) and close x
        if abs(w["y"] - last["y"]) <= max_gap_y and abs(w["left"] - (last["left"] + last["width"])) <= max_gap_x:
            current.append(w)
        else:
            # Save current phrase
            phrases.append(_make_phrase(current))
            current = [w]
    if current:
        phrases.append(_make_phrase(current))
    return phrases


def _make_phrase(words: list) -> dict:
    text = " ".join(w["text"] for w in words)
    left = min(w["left"] for w in words)
    top = min(w["top"] for w in words)
    right = max(w["left"] + w["width"] for w in words)
    bottom = max(w["top"] + w["height"] for w in words)
    return {
        "text": text,
        "x": (left + right) // 2,
        "y": (top + bottom) // 2,
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top,
        "conf": min(w["conf"] for w in words),
    }


def _detect_ui_elements(img) -> list:
    """Detect clickable UI regions using color/contrast analysis."""
    elements = []
    try:
        import numpy as np
        arr = np.array(img.convert("L"))
        h, w = arr.shape
        cols, rows = 12, 8
        cell_w = w // cols
        cell_h = h // rows
        for row in range(rows):
            for col in range(cols):
                region = arr[row*cell_h:(row+1)*cell_h, col*cell_w:(col+1)*cell_w]
                if region.size == 0:
                    continue
                avg = float(region.mean())
                std = float(region.std())
                if std > 35:  # high contrast = likely interactive element
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
    """
    Find where specific text appears on screen and return its coordinates.
    Uses fuzzy matching to handle OCR errors.
    """
    try:
        result = capture_and_read()
        phrases = result.get("phrases", [])
        words = result.get("words", [])
        search_lower = search_text.lower()

        # 1. Exact phrase match
        for phrase in phrases:
            if search_lower in phrase["text"].lower():
                return {"type": "found", "matches": [phrase], "count": 1, "match_type": "phrase"}

        # 2. Word match
        for word in words:
            if search_lower in word["text"].lower():
                return {"type": "found", "matches": [word], "count": 1, "match_type": "word"}

        # 3. Fuzzy match (character overlap)
        best = None
        best_score = 0.0
        for phrase in phrases:
            score = _fuzzy_score(search_lower, phrase["text"].lower())
            if score > best_score and score > 0.6:
                best_score = score
                best = phrase
        if best:
            return {"type": "found", "matches": [best], "count": 1, "match_type": "fuzzy", "score": round(best_score, 2)}

        return {"type": "not_found", "search": search_text, "phrases_seen": [p["text"] for p in phrases[:20]]}
    except Exception as exc:
        return {"type": "error", "error": str(exc)}


def _fuzzy_score(a: str, b: str) -> float:
    """Simple overlap score for fuzzy matching."""
    if not a or not b:
        return 0.0
    a_set = set(a)
    b_set = set(b)
    inter = len(a_set & b_set)
    union = len(a_set | b_set)
    if union == 0:
        return 0.0
    # Also check substring containment
    if a in b or b in a:
        return 1.0
    return inter / union


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

"""
tools/automation.py — JARVIS OMEGA V8 (COMPLETE FIX)
FIXES:
 1. Chrome explicitly used for YouTube/websites (not default browser)
 2. Window activation before typing — types in CORRECT window (Notepad, not chat)
 3. Added save_as action (Ctrl+Shift+S)
 4. Better app detection and fallback
 5. All actions activate target window first
"""
from __future__ import annotations

import os, re, subprocess, time, webbrowser, platform
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

BASE = Path(__file__).resolve().parent.parent

# ── Optional deps ─────────────────────────────────────────────────────────────
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    PYAUTOGUI = True
except ImportError:
    PYAUTOGUI = False

try:
    import pygetwindow as gw
    PYGETWINDOW = True
except ImportError:
    PYGETWINDOW = False

try:
    from PIL import ImageGrab
    PIL = True
except ImportError:
    PIL = False

try:
    import pytesseract
    TESSERACT = True
except ImportError:
    TESSERACT = False

# ══════════════════════════════════════════════════════════════════════════════
# CHROME PATH DETECTION
# ══════════════════════════════════════════════════════════════════════════════
def _find_chrome() -> Optional[str]:
    """Find Chrome executable path."""
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return None

_CHROME_PATH = _find_chrome()

# ══════════════════════════════════════════════════════════════════════════════
# WINDOW HELPERS — CRITICAL: Activate window before any action
# ══════════════════════════════════════════════════════════════════════════════
def _activate_window(title_pattern: str, timeout: float = 2.0) -> bool:
    """Activate window by title pattern. Returns True if found."""
    if not PYGETWINDOW:
        return False
    try:
        start = time.time()
        while time.time() - start < timeout:
            wins = gw.getWindowsWithTitle(title_pattern)
            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.3)  # Let window come to front
                return True
            time.sleep(0.2)
    except Exception as e:
        print(f"[AUTO] Window activation error: {e}")
    return False

def _find_window(title_pattern: str) -> Optional[object]:
    """Find window by title pattern."""
    if not PYGETWINDOW:
        return None
    try:
        wins = gw.getWindowsWithTitle(title_pattern)
        if wins:
            return wins[0]
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# APP REGISTRY
# ══════════════════════════════════════════════════════════════════════════════
_APPS: dict[str, str | list] = {
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox": r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "notepad": "notepad.exe",
    "wordpad": "wordpad.exe",
    "paint": "mspaint.exe",
    "calculator": "calc.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "explorer": "explorer.exe",
    "settings": "ms-settings:",
    "vscode": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe")],
    "spotify": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe")],
    "whatsapp": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\WhatsApp\WhatsApp.exe")],
    "telegram": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Telegram Desktop\Telegram.exe")],
    "discord": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Discord\Discord.exe")],
    "zoom": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Zoom\bin\Zoom.exe")],
    "teams": [os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Roaming\Microsoft\Teams\current\Teams.exe")],
}

_WEB_FALLBACKS = {
    "youtube": "https://youtube.com",
    "netflix": "https://netflix.com",
    "amazon": "https://amazon.in",
    "flipkart": "https://flipkart.com",
    "gmail": "https://gmail.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "chatgpt": "https://chat.openai.com",
    "github": "https://github.com",
    "linkedin": "https://linkedin.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "twitter": "https://twitter.com",
    "reddit": "https://reddit.com",
    "wikipedia": "https://wikipedia.org",
}

def _resolve_path(raw: str | list) -> Optional[str]:
    paths = raw if isinstance(raw, list) else [raw]
    for p in paths:
        p = os.path.expandvars(p)
        if os.path.exists(p):
            return p
        if not os.sep in p and not p.startswith("ms-"):
            return p
    return None


# ══════════════════════════════════════════════════════════════════════════════
# OPEN APP — FIXED: YouTube opens in Chrome, not as app
# ══════════════════════════════════════════════════════════════════════════════
def _open_app(name: str) -> Tuple[bool, str]:
    nl = name.lower().strip()

    # Check web fallbacks FIRST (YouTube, Netflix, etc.)
    if nl in _WEB_FALLBACKS:
        url = _WEB_FALLBACKS[nl]
        return _open_in_chrome(url)

    # Direct registry lookup
    entry = _APPS.get(nl)
    if entry:
        path = _resolve_path(entry)
        if path:
            try:
                if path.startswith("ms-"):
                    os.startfile(path)
                else:
                    subprocess.Popen([path], creationflags=subprocess.CREATE_NEW_CONSOLE if path.endswith("cmd.exe") else 0)
                return True, f"{name.title()} khul gaya, Sir!"
            except Exception as e:
                return False, f"Error: {e}"

    # Partial match
    for key, entry in _APPS.items():
        if nl in key or key in nl:
            path = _resolve_path(entry)
            if path:
                try:
                    subprocess.Popen([path])
                    return True, f"{key.title()} khul gaya, Sir!"
                except Exception as e:
                    return False, f"Error opening {key}: {e}"

    # Last resort: search
    url = f"https://www.google.com/search?q={name.replace(' ', '+')}"
    return _open_in_chrome(url)


def _open_in_chrome(url: str) -> Tuple[bool, str]:
    """Open URL specifically in Chrome browser."""
    if _CHROME_PATH and os.path.exists(_CHROME_PATH):
        try:
            subprocess.Popen([_CHROME_PATH, url])
            return True, f"Chrome mein khul gaya: {url}"
        except Exception as e:
            print(f"[AUTO] Chrome open error: {e}")
    # Fallback to default browser
    webbrowser.open(url)
    return True, f"Browser mein khul gaya: {url}"


# ══════════════════════════════════════════════════════════════════════════════
# WEB ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _search_web(query: str) -> Tuple[bool, str]:
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    return _open_in_chrome(url)

def _search_youtube(query: str) -> Tuple[bool, str]:
    url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
    return _open_in_chrome(url)

def _open_url(url: str) -> Tuple[bool, str]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return _open_in_chrome(url)

def _play_music(query: str) -> Tuple[bool, str]:
    spotify_uri = f"spotify:search:{query.replace(' ', '%20')}"
    try:
        os.startfile(spotify_uri)
        return True, f"Spotify pe '{query}' play ho raha hai, Sir!"
    except Exception:
        pass
    return _search_youtube(f"{query} song")


# ══════════════════════════════════════════════════════════════════════════════
# TYPE TEXT — FIXED: Activates Notepad first, then types there
# ══════════════════════════════════════════════════════════════════════════════
def _type_text(text: str, target_app: str = "") -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed — run: python -m pip install pyautogui"

    try:
        # CRITICAL FIX: If target app specified, activate it first
        if target_app:
            # Try to find and activate the target window
            activated = _activate_window(target_app, timeout=3.0)
            if not activated:
                # Try common variations
                for pattern in [target_app, target_app.title(), target_app.lower(), target_app.upper()]:
                    if _activate_window(pattern, timeout=1.0):
                        activated = True
                        break
            if not activated:
                print(f"[AUTO] Warning: Could not activate '{target_app}', typing at current cursor position")

        # Small delay to ensure window is active
        time.sleep(0.5)

        # Type the text
        pyautogui.write(text, interval=0.01)
        return True, f"Text type kar diya: '{text[:50]}{'...' if len(text) > 50 else ''}'"
    except Exception as e:
        return False, f"Type error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# SAVE FILE — NEW ACTION
# ══════════════════════════════════════════════════════════════════════════════
def _save_file(target_app: str = "") -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        if target_app:
            _activate_window(target_app, timeout=2.0)
            time.sleep(0.3)
        pyautogui.hotkey("ctrl", "s")
        return True, "Save dialog khul gaya, Sir!"
    except Exception as e:
        return False, f"Save error: {e}"

def _save_as(target_app: str = "") -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        if target_app:
            _activate_window(target_app, timeout=2.0)
            time.sleep(0.3)
        pyautogui.hotkey("ctrl", "shift", "s")
        return True, "Save As dialog khul gaya, Sir!"
    except Exception as e:
        return False, f"Save As error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# MOUSE CONTROL
# ══════════════════════════════════════════════════════════════════════════════
def _mouse_move(x: int, y: int) -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        pyautogui.moveTo(x, y, duration=0.5)
        return True, f"Mouse ({x}, {y}) pe gayi"
    except Exception as e:
        return False, f"Mouse move error: {e}"

def _mouse_click(x: Optional[int] = None, y: Optional[int] = None, 
                 button: str = "left") -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        if x is not None and y is not None:
            pyautogui.click(x, y, button=button)
            return True, f"Mouse click ({x}, {y}) {button} button"
        else:
            pyautogui.click(button=button)
            return True, f"Mouse click {button} button"
    except Exception as e:
        return False, f"Click error: {e}"

def _mouse_scroll(clicks: int) -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        return True, f"Mouse scroll {direction}"
    except Exception as e:
        return False, f"Scroll error: {e}"

def _mouse_position() -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        x, y = pyautogui.position()
        return True, f"Mouse position: ({x}, {y})"
    except Exception as e:
        return False, f"Position error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# KEYBOARD / SCREEN ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _hotkey(keys: str) -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        parts = [k.strip() for k in keys.replace("+", " ").split()]
        pyautogui.hotkey(*parts)
        return True, f"Hotkey '{keys}' press hua"
    except Exception as e:
        return False, f"Hotkey error: {e}"

def _screenshot() -> Tuple[bool, str]:
    if not PIL:
        if PYAUTOGUI:
            pyautogui.hotkey("win", "printscreen")
            return True, "Screenshot le liya — Pictures/Screenshots mein milega"
        return False, "PIL not installed"
    shots_dir = BASE / "data" / "screenshots"
    shots_dir.mkdir(parents=True, exist_ok=True)
    fname = shots_dir / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        img = ImageGrab.grab()
        img.save(str(fname))
        return True, f"Screenshot save hua: {fname.name}"
    except Exception as e:
        return False, f"Screenshot error: {e}"

def _read_screen() -> Tuple[bool, str]:
    if not PIL:
        return False, "PIL not installed"
    if not TESSERACT:
        return False, ("pytesseract not installed — run: pip install pytesseract\n"
                       "Also install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
    try:
        img = ImageGrab.grab()
        text = pytesseract.image_to_string(img, lang="eng+hin")
        text = text.strip()
        return True, text[:800] if text else "Screen pe koi readable text nahi mila"
    except Exception as e:
        return False, f"Screen read error: {e}"


# ══════════════════════════════════════════════════════════════════════════════
# VOLUME & SYSTEM CONTROLS
# ══════════════════════════════════════════════════════════════════════════════
def _volume_up() -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    for _ in range(5):
        pyautogui.press("volumeup")
    return True, "Volume badh gaya, Sir!"

def _volume_down() -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    for _ in range(5):
        pyautogui.press("volumedown")
    return True, "Volume kam ho gaya, Sir!"

def _mute() -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    pyautogui.press("volumemute")
    return True, "Mute ho gaya, Sir!"

def _lock_screen() -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    pyautogui.hotkey("win", "l")
    return True, "Screen lock ho gayi, Sir!"

def _shutdown() -> Tuple[bool, str]:
    return False, "Shutdown cancelled — yeh dangerous command hai, Sir. Aap manually karein."


# ══════════════════════════════════════════════════════════════════════════════
# WINDOW MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
def _minimize_app(name: str) -> Tuple[bool, str]:
    if not PYGETWINDOW:
        if PYAUTOGUI:
            pyautogui.hotkey("win", "down")
            return True, "Window minimize ho gayi"
        return False, "pygetwindow not installed"
    wins = gw.getWindowsWithTitle(name)
    if wins:
        wins[0].minimize()
        return True, f"'{name}' minimize ho gaya, Sir!"
    return False, f"'{name}' window nahi mili"

def _maximize_app(name: str) -> Tuple[bool, str]:
    if not PYGETWINDOW:
        if PYAUTOGUI:
            pyautogui.hotkey("win", "up")
            return True, "Window maximize ho gayi"
        return False, "pygetwindow not installed"
    wins = gw.getWindowsWithTitle(name)
    if wins:
        wins[0].maximize()
        return True, f"'{name}' maximize ho gaya, Sir!"
    return False, f"'{name}' window nahi mili"

def _close_app(name: str) -> Tuple[bool, str]:
    nl = name.lower().strip()
    if PYGETWINDOW:
        wins = gw.getWindowsWithTitle(nl)
        if wins:
            wins[0].close()
            return True, f"'{name}' band kar diya, Sir!"
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", f"{nl}.exe"],
            capture_output=True, text=True)
        if result.returncode == 0:
            return True, f"'{name}' band ho gaya, Sir!"
    except Exception:
        pass
    return False, f"'{name}' nahi mila band karne ke liye"


def _click_text(target: str) -> Tuple[bool, str]:
    if not PYAUTOGUI:
        return False, "pyautogui not installed"
    try:
        loc = pyautogui.locateOnScreen(target, confidence=0.8)
        if loc:
            pyautogui.click(loc)
            return True, f"'{target}' click ho gaya"
    except Exception:
        pass
    return False, f"'{target}' screen pe nahi mila"


# ══════════════════════════════════════════════════════════════════════════════
# CENTRAL EXECUTOR
# ══════════════════════════════════════════════════════════════════════════════
class Automation:
    """Thin wrapper exposing execute(action_dict) → (success, message)."""

    def execute(self, action: dict) -> Tuple[bool, str]:
        act = (action.get("action") or "").strip().lower()
        target = (action.get("target") or "").strip()
        print(f"[AUTO] {act!r} → target={target!r}")

        dispatch = {
            # Apps
            "open_app": lambda: _open_app(target),
            "close_app": lambda: _close_app(target),

            # Web
            "search_web": lambda: _search_web(target),
            "search_youtube": lambda: _search_youtube(target),
            "play_music": lambda: _play_music(target),
            "open_url": lambda: _open_url(target),

            # Mouse
            "mouse_move": lambda: _mouse_move(
                int(target.split(',')[0]) if ',' in target else 500,
                int(target.split(',')[1]) if ',' in target else 500),
            "mouse_click": lambda: _mouse_click(),
            "right_click": lambda: _mouse_click(button="right"),
            "mouse_scroll_up": lambda: _mouse_scroll(5),
            "mouse_scroll_down": lambda: _mouse_scroll(-5),
            "mouse_position": lambda: _mouse_position(),

            # Keyboard/Screen — FIXED: pass target_app for window activation
            "screenshot": lambda: _screenshot(),
            "read_screen": lambda: _read_screen(),
            "type_text": lambda: _type_text(target, action.get("app", "")),
            "hotkey": lambda: _hotkey(target),
            "click_text": lambda: _click_text(target),
            "scroll_down": lambda: _mouse_scroll(-3),
            "scroll_up": lambda: _mouse_scroll(3),

            # Save — NEW ACTIONS
            "save_file": lambda: _save_file(action.get("app", "")),
            "save_as": lambda: _save_as(action.get("app", "")),

            # Volume/System
            "volume_up": lambda: _volume_up(),
            "volume_down": lambda: _volume_down(),
            "mute": lambda: _mute(),
            "lock_screen": lambda: _lock_screen(),
            "shutdown": lambda: _shutdown(),

            # Window
            "minimize_app": lambda: _minimize_app(target),
            "maximize_app": lambda: _maximize_app(target),
        }

        fn = dispatch.get(act)
        if fn:
            try:
                return fn()
            except Exception as e:
                return False, f"Action '{act}' mein error aaya: {e}"

        return False, f"Unknown action: '{act}'"

    def execute_all(self, actions: list) -> list[Tuple[bool, str]]:
        results = []
        for a in actions:
            ok, msg = self.execute(a)
            results.append((ok, msg))
            if not ok:
                print(f"[AUTO] ✗ {msg}")
            else:
                print(f"[AUTO] ✓ {msg}")
            time.sleep(0.15)
        return results
"""
tools/tool_manager.py — JARVIS OMEGA V3 Tool Dispatcher
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES vs V2:
  ✅ install_skill now works (pip install in real-time)
  ✅ generate_image returns result to GUI for display
  ✅ read_screen returns usable text + element positions
  ✅ open_app uses subprocess.Popen properly
  ✅ python runner uses sys.executable (correct Python)
  ✅ file saving goes to user documents folder
"""

import logging
import subprocess
import sys
import webbrowser
import platform
import time
import os
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger("JARVIS.TOOLS")
OS = platform.system()


class ToolManager:
    def __init__(self, settings: dict, gui_callback: Optional[Callable] = None):
        self.settings     = settings
        self.gui_callback = gui_callback
        self._win_ctrl    = None
        self._web_ctrl    = None
        self._minimize_cb: Optional[Callable] = None

    def set_minimize_callback(self, cb: Callable):
        self._minimize_cb = cb

    def execute(self, action: str, params: dict) -> dict:
        try:
            # App lifecycle
            if action == "open_app":          return self._open_app(params)
            if action == "close_app":         return self._close_app(params)
            if action == "open_url":          return self._open_url(params)
            # App control
            if action == "attach_app":        return self._attach_app(params)
            if action == "read_ui_tree":      return self._read_ui_tree(params)
            if action == "click_element":     return self._click_element(params)
            if action == "type_in_element":   return self._type_in_element(params)
            if action == "read_element_text": return self._read_element_text(params)
            # Web control
            if action == "open_web_browser":  return self._open_web_browser(params)
            if action == "click_web_element": return self._click_web_element(params)
            if action == "type_in_web":       return self._type_in_web(params)
            if action == "read_page":         return self._read_page(params)
            if action == "web_navigate":      return self._web_navigate(params)
            # Mouse/keyboard
            if action == "type_text":         return self._type_text(params)
            if action == "click_at":          return self._click_at(params)
            if action == "move_mouse":        return self._move_mouse(params)
            if action == "scroll":            return self._scroll(params)
            if action == "hotkey":            return self._hotkey(params)
            # Screen
            if action == "screenshot":        return self._screenshot(params)
            if action == "read_screen":       return self._read_screen(params)
            if action == "find_on_screen":    return self._find_on_screen(params)
            # Code
            if action == "run_code":          return self._run_code(params)
            if action == "create_file":       return self._create_file(params)
            if action == "create_project":    return self._create_project(params)
            if action == "save_file":         return self._save_file(params)
            # Web search
            if action == "web_search":        return self._web_search(params)
            # System
            if action == "system_cmd":        return self._system_cmd(params)
            if action == "set_volume":        return self._set_volume(params)
            if action == "system_info":       return self._system_info(params)
            if action == "install_skill":     return self._install_skill(params)
            # Hardware
            if action == "arduino_upload":    return self._arduino_upload(params)
            if action == "arduino_monitor":   return self._arduino_monitor(params)
            if action == "generate_image":    return self._generate_image(params)

            logger.warning("Unknown action: %s", action)
            return {"type": "error", "error": f"Unknown action: {action}"}
        except Exception as exc:
            logger.error("Tool error [%s]: %s", action, exc, exc_info=True)
            return {"type": "error", "error": str(exc)}

    # ── App lifecycle ──────────────────────────────────────────────────────────

    APP_MAP = {
        "chrome":       {"Windows": "chrome",      "Darwin": "open -a 'Google Chrome'", "Linux": "google-chrome"},
        "firefox":      {"Windows": "firefox",     "Darwin": "open -a Firefox",         "Linux": "firefox"},
        "notepad":      {"Windows": "notepad",     "Darwin": "open -a TextEdit",        "Linux": "gedit"},
        "calculator":   {"Windows": "calc",        "Darwin": "open -a Calculator",      "Linux": "gnome-calculator"},
        "terminal":     {"Windows": "cmd",         "Darwin": "open -a Terminal",        "Linux": "x-terminal-emulator"},
        "explorer":     {"Windows": "explorer",    "Darwin": "open .",                  "Linux": "xdg-open ."},
        "vscode":       {"Windows": "code",        "Darwin": "code",                    "Linux": "code"},
        "code":         {"Windows": "code",        "Darwin": "code",                    "Linux": "code"},
        "spotify":      {"Windows": "spotify",     "Darwin": "open -a Spotify",         "Linux": "spotify"},
        "discord":      {"Windows": "discord",     "Darwin": "open -a Discord",         "Linux": "discord"},
        "vlc":          {"Windows": "vlc",         "Darwin": "open -a VLC",             "Linux": "vlc"},
        "paint":        {"Windows": "mspaint",     "Darwin": "open -a Paintbrush",      "Linux": "gimp"},
        "cmd":          {"Windows": "cmd",         "Darwin": "open -a Terminal",        "Linux": "bash"},
        "powershell":   {"Windows": "powershell",  "Darwin": "open -a Terminal",        "Linux": "bash"},
        "task manager": {"Windows": "taskmgr",     "Darwin": "open -a 'Activity Monitor'", "Linux": "gnome-system-monitor"},
        "blender":      {"Windows": "blender",     "Darwin": "open -a Blender",         "Linux": "blender"},
        "excel":        {"Windows": "excel",       "Darwin": "open -a 'Microsoft Excel'","Linux": "libreoffice --calc"},
        "word":         {"Windows": "winword",     "Darwin": "open -a 'Microsoft Word'","Linux": "libreoffice --writer"},
        "obs":          {"Windows": "obs64",       "Darwin": "open -a OBS",             "Linux": "obs"},
        "notepad++":    {"Windows": "notepad++",   "Darwin": "open -a TextEdit",        "Linux": "gedit"},
        "snipping tool":{"Windows": "snippingtool","Darwin": "screencapture -i /tmp/snip.png", "Linux": "gnome-screenshot"},
    }

    URL_APPS = {
        "youtube":    "https://youtube.com",
        "gmail":      "https://mail.google.com",
        "maps":       "https://maps.google.com",
        "drive":      "https://drive.google.com",
        "whatsapp":   "https://web.whatsapp.com",
        "github":     "https://github.com",
        "stackoverflow": "https://stackoverflow.com",
        "chatgpt":    "https://chat.openai.com",
        "netflix":    "https://netflix.com",
        "amazon":     "https://amazon.in",
        "flipkart":   "https://flipkart.com",
        "instagram":  "https://instagram.com",
        "twitter":    "https://twitter.com",
        "facebook":   "https://facebook.com",
        "linkedin":   "https://linkedin.com",
    }

    def _open_app(self, params: dict) -> dict:
        app = params.get("app", "").lower().strip()
        if app in self.URL_APPS:
            webbrowser.open(self.URL_APPS[app])
            return {"type": "app_opened", "app": app, "method": "browser"}
        if app.startswith(("http://", "https://", "www.")):
            webbrowser.open(app if "://" in app else f"https://{app}")
            return {"type": "app_opened", "app": app, "method": "url"}
        cmd_map = self.APP_MAP.get(app)
        if cmd_map:
            cmd = cmd_map.get(OS)
            if cmd:
                subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE if OS == "Windows" else 0)
                time.sleep(1.5)
                return {"type": "app_opened", "app": app}
        # Try directly
        try:
            subprocess.Popen(app, shell=True)
            time.sleep(1.5)
            return {"type": "app_opened", "app": app}
        except Exception as exc:
            return {"type": "error", "error": f"Cannot open '{app}': {exc}"}

    def _close_app(self, params: dict) -> dict:
        try:
            import psutil
            app = params.get("app", "").lower()
            closed = []
            for proc in psutil.process_iter(["name", "pid"]):
                try:
                    if app in proc.info["name"].lower():
                        proc.kill()
                        closed.append(proc.info["name"])
                except Exception:
                    pass
            return {"type": "app_closed", "closed": closed}
        except ImportError:
            return {"type": "error", "error": "psutil not installed. pip install psutil"}

    def _open_url(self, params: dict) -> dict:
        url = params.get("url", "")
        if url:
            webbrowser.open(url)
        return {"type": "url_opened", "url": url}

    # ── App control (pywinauto) ────────────────────────────────────────────────

    def _get_win_ctrl(self):
        if self._win_ctrl is None:
            from tools.app_controller import WindowsAppController
            self._win_ctrl = WindowsAppController()
        return self._win_ctrl

    def _attach_app(self, params: dict) -> dict:
        ctrl = self._get_win_ctrl()
        return ctrl.attach(params.get("app", ""), params.get("title"), params.get("timeout", 5))

    def _read_ui_tree(self, params: dict) -> dict:
        return self._get_win_ctrl().read_ui_tree(params.get("depth", 3))

    def _click_element(self, params: dict) -> dict:
        return self._get_win_ctrl().click_element(params.get("element", params.get("name", "")), params.get("partial", True))

    def _type_in_element(self, params: dict) -> dict:
        return self._get_win_ctrl().type_in_element(params.get("element", params.get("field", "")), params.get("text", ""), params.get("clear_first", True))

    def _read_element_text(self, params: dict) -> dict:
        return self._get_win_ctrl().read_element_text(params.get("element", ""))

    # ── Web control (Selenium) ─────────────────────────────────────────────────

    def _get_web_ctrl(self):
        if self._web_ctrl is None:
            from tools.app_controller import WebAppController
            self._web_ctrl = WebAppController()
        return self._web_ctrl

    def _open_web_browser(self, params: dict) -> dict:
        return self._get_web_ctrl().open(params.get("url", "https://google.com"), params.get("browser", "chrome"))

    def _click_web_element(self, params: dict) -> dict:
        return self._get_web_ctrl().click_web_element(params.get("text", ""), params.get("selector", ""), params.get("by", "text"))

    def _type_in_web(self, params: dict) -> dict:
        return self._get_web_ctrl().type_in_web_element(params.get("text", ""), params.get("placeholder", ""), params.get("label", ""), params.get("selector", ""))

    def _read_page(self, params: dict) -> dict:
        return self._get_web_ctrl().read_page_text(params.get("max_chars", 2000))

    def _web_navigate(self, params: dict) -> dict:
        return self._get_web_ctrl().navigate(params.get("url", ""))

    # ── Mouse/Keyboard (pyautogui) ─────────────────────────────────────────────

    def _type_text(self, params: dict) -> dict:
        try:
            import pyautogui
            delay = params.get("delay", 0.5)
            if delay > 0:
                time.sleep(delay)
            text = params.get("text", "")
            pyautogui.write(text, interval=0.03)
            if params.get("press_enter"):
                pyautogui.press("enter")
            return {"type": "text_typed", "text": text[:50]}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _click_at(self, params: dict) -> dict:
        try:
            import pyautogui
            x, y   = params.get("x", 0), params.get("y", 0)
            button = params.get("button", "left")
            pyautogui.click(x, y, button=button)
            return {"type": "clicked", "x": x, "y": y}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _move_mouse(self, params: dict) -> dict:
        try:
            import pyautogui
            pyautogui.moveTo(params.get("x", 0), params.get("y", 0), duration=0.3)
            return {"type": "mouse_moved"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _scroll(self, params: dict) -> dict:
        try:
            import pyautogui
            direction = params.get("direction", "down")
            amount    = params.get("amount", 3)
            pyautogui.scroll(amount if direction == "up" else -amount)
            return {"type": "scrolled", "direction": direction}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _hotkey(self, params: dict) -> dict:
        try:
            import pyautogui
            keys = params.get("keys", "").split("+")
            pyautogui.hotkey(*keys)
            return {"type": "hotkey_pressed", "keys": params.get("keys", "")}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    # ── Screen ─────────────────────────────────────────────────────────────────

    def _screenshot(self, params: dict) -> dict:
        try:
            import pyautogui
            path = params.get("path", "data/screenshots/screenshot.png")
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            img = pyautogui.screenshot()
            img.save(path)
            return {"type": "screenshot_taken", "path": path}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _read_screen(self, params: dict) -> dict:
        from tools.vision_tools import capture_and_read
        return capture_and_read()

    def _find_on_screen(self, params: dict) -> dict:
        from tools.vision_tools import find_text_on_screen
        return find_text_on_screen(params.get("text", ""))

    # ── Code Execution ─────────────────────────────────────────────────────────

    def _run_code(self, params: dict) -> dict:
        code    = params.get("code", "")
        lang    = params.get("language", "python").lower()
        save_as = params.get("save_as", "")
        if not code.strip():
            return {"type": "error", "error": "No code provided"}

        if save_as:
            path = Path("data/projects") / save_as
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")

        if self._minimize_cb:
            try:
                self._minimize_cb(True)
            except Exception:
                pass

        try:
            if lang == "python":
                result = self._run_python(code, save_as)
            else:
                result = {"type": "code_result", "code": code,
                          "stdout": f"[{lang} execution not supported yet]"}
        finally:
            if self._minimize_cb:
                try:
                    self._minimize_cb(False)
                except Exception:
                    pass
        return result

    def _run_python(self, code: str, filename: str = "") -> dict:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False, encoding="utf-8") as f:
            f.write(code)
            fname = f.name
        try:
            result = subprocess.run(
                [sys.executable, fname],  # FIXED: use sys.executable = current Python
                capture_output=True, text=True, timeout=30
            )
            stdout = (result.stdout + result.stderr).strip()
            return {
                "type":       "code_result",
                "code":       code,
                "stdout":     stdout[:5000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"type": "code_result", "code": code, "stdout": "[Timeout after 30s — code still running]"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _create_file(self, params: dict) -> dict:
        path_str = params.get("path", "output.txt")
        content  = params.get("content", "")
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Created file: %s", path)
        return {"type": "file_created", "path": str(path.resolve())}

    def _save_file(self, params: dict) -> dict:
        """Save file to Documents or user-specified location."""
        content  = params.get("content", "")
        filename = params.get("filename", "jarvis_output.txt")
        folder   = params.get("folder", "")

        if not folder:
            # Save to Documents
            docs = Path.home() / "Documents" / "JARVIS"
            docs.mkdir(parents=True, exist_ok=True)
            path = docs / filename
        else:
            path = Path(folder) / filename
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(content, encoding="utf-8")
        logger.info("Saved file: %s", path)
        return {"type": "file_saved", "path": str(path.resolve())}

    def _create_project(self, params: dict) -> dict:
        from tools.code_tools import create_project_scaffold
        return create_project_scaffold(params.get("name", "my_project"), params.get("type", "python"), params.get("description", ""))

    # ── Web search ─────────────────────────────────────────────────────────────

    def _web_search(self, params: dict) -> dict:
        from tools.web_tools import web_search
        return web_search(params.get("query", ""))

    # ── System ─────────────────────────────────────────────────────────────────

    def _system_cmd(self, params: dict) -> dict:
        cmd = params.get("command", "")
        if not cmd:
            return {"type": "error", "error": "No command provided"}
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True,
                                    text=True, timeout=15)
            return {
                "type":       "system_result",
                "stdout":     (result.stdout + result.stderr)[:2000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"type": "error", "error": "Command timed out"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _set_volume(self, params: dict) -> dict:
        level = params.get("level", 50)
        try:
            if OS == "Windows":
                subprocess.run(f"nircmd.exe setsysvolume {int(level * 655.35)}", shell=True)
            elif OS == "Linux":
                subprocess.run(f"amixer set Master {level}%", shell=True)
            elif OS == "Darwin":
                subprocess.run(f"osascript -e 'set volume output volume {level}'", shell=True)
            return {"type": "volume_set", "level": level}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _system_info(self, params: dict) -> dict:
        from tools.system_tools import get_system_info
        return get_system_info()

    def _install_skill(self, params: dict) -> dict:
        """Actually installs a Python package via pip."""
        skill = params.get("skill", "").strip()
        SKILL_MAP = {
            "blender":    ["bpy"],
            "arduino":    ["pyserial", "esptool"],
            "unity":      ["unitypy"],
            "photoshop":  ["photoshop-python-api"],
            "selenium":   ["selenium", "webdriver-manager"],
            "pyautogui":  ["pyautogui"],
            "pywinauto":  ["pywinauto"],
            "psutil":     ["psutil"],
            "pillow":     ["pillow"],
            "tesseract":  ["pytesseract"],
            "whisper":    ["openai-whisper"],
            "groq":       ["groq"],
        }
        packages = SKILL_MAP.get(skill.lower(), [skill])
        results  = []
        for pkg in packages:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg, "--quiet"],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    results.append(f"✅ {pkg} installed")
                else:
                    results.append(f"⚠️ {pkg}: {result.stderr[:100]}")
            except Exception as exc:
                results.append(f"❌ {pkg}: {exc}")
        return {"type": "skill_installed", "skill": skill, "results": results,
                "message": "\n".join(results)}

    # ── Arduino ────────────────────────────────────────────────────────────────

    def _arduino_upload(self, params: dict) -> dict:
        from tools.arduino_tools import upload_sketch
        return upload_sketch(code=params.get("code", ""), port=params.get("port", "auto"))

    def _arduino_monitor(self, params: dict) -> dict:
        from tools.arduino_tools import read_serial
        return read_serial(port=params.get("port", "auto"), baud=params.get("baud", 9600))

    # ── Image Generation ───────────────────────────────────────────────────────

    def _generate_image(self, params: dict) -> dict:
        from tools.image_tools import generate_image
        result = generate_image(
            prompt=params.get("prompt", ""),
            style=params.get("style", "photorealistic"),
        )
        # Notify GUI to display the image
        if self.gui_callback and result.get("type") == "image":
            self.gui_callback("image_result", "generate_image", result)
        return result

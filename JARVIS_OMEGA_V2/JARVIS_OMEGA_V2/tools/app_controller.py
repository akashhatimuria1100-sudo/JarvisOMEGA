"""
tools/app_controller.py — JARVIS OMEGA V2 App Controller
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEW MODULE — fixes "AI can open apps but not control them"

Features:
  • Attach to any open Windows app by name or title
  • Read the full UI element tree (buttons, fields, menus, etc.)
  • Click elements by their visible label — NOT by raw x/y coords
  • Type into fields by label
  • Web app control via Selenium (Chrome/Edge)
  • Smart element search: finds "Save", "Submit", "OK" etc. automatically
"""

import logging
import time
import subprocess
import platform
from typing import Optional

logger = logging.getLogger("JARVIS.APPCTRL")
OS = platform.system()


# ══════════════════════════════════════════════════════════════════════════════
#  Windows App Controller (pywinauto)
# ══════════════════════════════════════════════════════════════════════════════

class WindowsAppController:
    """Control any Windows application via UI Automation."""

    def __init__(self):
        self._app  = None
        self._win  = None
        self._backend = "uia"   # "uia" = modern apps; "win32" = legacy

    def attach(self, app_name: str, title_pattern: str = None, timeout: int = 5) -> dict:
        """
        Attach to a running application.
        app_name: process name like "notepad.exe", "chrome.exe", "code.exe"
        title_pattern: window title substring (optional)
        """
        try:
            from pywinauto import Application, Desktop
            from pywinauto.findwindows import ElementNotFoundError

            # Try UI Automation first, fall back to win32
            for backend in ("uia", "win32"):
                try:
                    if title_pattern:
                        app = Application(backend=backend).connect(
                            title_re=f".*{title_pattern}.*", timeout=timeout
                        )
                    else:
                        app = Application(backend=backend).connect(
                            path=app_name, timeout=timeout
                        )
                    self._app = app
                    self._backend = backend
                    # Get main window
                    self._win = app.top_window()
                    logger.info("Attached to '%s' using %s backend", app_name, backend)
                    return {"type": "attached", "app": app_name, "backend": backend,
                            "title": self._win.window_text()}
                except Exception:
                    continue

            return {"type": "error", "error": f"Could not attach to '{app_name}'"}
        except ImportError:
            return {"type": "error", "error": "pywinauto not installed. Run: pip install pywinauto"}

    def read_ui_tree(self, depth: int = 3) -> dict:
        """Read the UI element tree — returns list of interactive elements."""
        if not self._win:
            return {"type": "error", "error": "No window attached. Call attach() first."}
        try:
            elements = []
            self._collect_elements(self._win, elements, depth=depth, current=0)
            return {"type": "ui_tree", "elements": elements, "count": len(elements)}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _collect_elements(self, parent, elements: list, depth: int, current: int):
        """Recursively collect clickable/typeable elements."""
        if current >= depth:
            return
        try:
            children = parent.children()
        except Exception:
            return
        for child in children:
            try:
                ctrl_type = child.element_info.control_type if hasattr(child, "element_info") else ""
                name = child.window_text() or ""
                if name and ctrl_type in ("Button", "Edit", "ComboBox", "MenuItem",
                                          "CheckBox", "RadioButton", "Hyperlink",
                                          "Text", "ToolBar", "TreeItem", "ListItem",
                                          "Button", "", None):
                    rect = child.rectangle()
                    elements.append({
                        "name": name,
                        "type": ctrl_type or "unknown",
                        "x": rect.left + (rect.right - rect.left) // 2,
                        "y": rect.top + (rect.bottom - rect.top) // 2,
                        "enabled": child.is_enabled() if hasattr(child, "is_enabled") else True,
                    })
            except Exception:
                pass
            self._collect_elements(child, elements, depth, current + 1)

    def click_element(self, element_name: str, partial: bool = True) -> dict:
        """Click a UI element by its visible label text."""
        if not self._win:
            return {"type": "error", "error": "No window attached."}
        try:
            # Try pywinauto direct find
            ctrl = self._find_element(element_name, partial)
            if ctrl:
                ctrl.click_input()
                logger.info("Clicked element: '%s'", element_name)
                return {"type": "clicked", "element": element_name}
            return {"type": "error", "error": f"Element '{element_name}' not found"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def type_in_element(self, element_name: str, text: str, clear_first: bool = True) -> dict:
        """Type text into a named input field."""
        if not self._win:
            return {"type": "error", "error": "No window attached."}
        try:
            ctrl = self._find_element(element_name, partial=True)
            if ctrl:
                ctrl.set_focus()
                if clear_first:
                    ctrl.set_text("")
                ctrl.type_keys(text, with_spaces=True)
                logger.info("Typed into '%s': %s", element_name, text[:40])
                return {"type": "typed", "element": element_name, "text": text[:40]}
            return {"type": "error", "error": f"Input field '{element_name}' not found"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def read_element_text(self, element_name: str) -> dict:
        """Read the text content of a named element."""
        if not self._win:
            return {"type": "error", "error": "No window attached."}
        try:
            ctrl = self._find_element(element_name, partial=True)
            if ctrl:
                text = ctrl.window_text() or ctrl.get_value() if hasattr(ctrl, "get_value") else ""
                return {"type": "element_text", "element": element_name, "text": text}
            return {"type": "error", "error": f"Element '{element_name}' not found"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _find_element(self, name: str, partial: bool = True):
        """Search the UI tree for an element by name."""
        try:
            if partial:
                return self._win.child_window(title_re=f".*{name}.*", found_index=0)
            else:
                return self._win.child_window(title=name, found_index=0)
        except Exception:
            return None

    def get_window_title(self) -> str:
        if self._win:
            try:
                return self._win.window_text()
            except Exception:
                pass
        return ""

    def screenshot_window(self, save_path: str = None) -> dict:
        """Take a screenshot of the attached window."""
        if not self._win:
            return {"type": "error", "error": "No window attached."}
        try:
            from PIL import Image
            import tempfile
            if not save_path:
                save_path = tempfile.mktemp(suffix=".png")
            img = self._win.capture_as_image()
            img.save(save_path)
            return {"type": "screenshot", "path": save_path}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}


# ══════════════════════════════════════════════════════════════════════════════
#  Web App Controller (Selenium)
# ══════════════════════════════════════════════════════════════════════════════

class WebAppController:
    """Control web applications using Selenium with auto-driver management."""

    def __init__(self):
        self._driver = None

    def open(self, url: str, browser: str = "chrome") -> dict:
        """Open a URL in a controlled browser."""
        try:
            self._init_driver(browser)
            self._driver.get(url)
            time.sleep(1.5)
            return {"type": "web_opened", "url": url, "title": self._driver.title}
        except ImportError:
            return {"type": "error", "error": "selenium not installed. Run: pip install selenium webdriver-manager"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def _init_driver(self, browser: str = "chrome"):
        if self._driver:
            return
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.edge.service import Service as EdgeService

        if browser.lower() in ("chrome", "google chrome"):
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                options = webdriver.ChromeOptions()
                options.add_argument("--start-maximized")
                self._driver = webdriver.Chrome(
                    service=ChromeService(ChromeDriverManager().install()),
                    options=options
                )
            except Exception:
                # Try without webdriver_manager
                self._driver = webdriver.Chrome()
        elif browser.lower() in ("edge", "msedge"):
            try:
                from webdriver_manager.microsoft import EdgeChromiumDriverManager
                self._driver = webdriver.Edge(
                    service=EdgeService(EdgeChromiumDriverManager().install())
                )
            except Exception:
                self._driver = webdriver.Edge()

    def click_web_element(self, text: str = None, selector: str = None,
                          by: str = "text") -> dict:
        """Click a web element by visible text, CSS selector, or ID."""
        if not self._driver:
            return {"type": "error", "error": "Browser not open. Call open() first."}
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(self._driver, 10)

            if by == "text" and text:
                # Try multiple strategies to find by text
                for strategy in [
                    f"//*[contains(text(), '{text}')]",
                    f"//button[contains(text(), '{text}')]",
                    f"//a[contains(text(), '{text}')]",
                    f"//*[@aria-label='{text}']",
                    f"//*[@placeholder='{text}']",
                ]:
                    try:
                        el = wait.until(EC.element_to_be_clickable((By.XPATH, strategy)))
                        el.click()
                        return {"type": "web_clicked", "text": text}
                    except Exception:
                        continue
                return {"type": "error", "error": f"Web element '{text}' not found"}
            elif selector:
                by_map = {"css": By.CSS_SELECTOR, "id": By.ID, "xpath": By.XPATH,
                          "name": By.NAME, "class": By.CLASS_NAME}
                loc = by_map.get(by, By.CSS_SELECTOR)
                el = wait.until(EC.element_to_be_clickable((loc, selector)))
                el.click()
                return {"type": "web_clicked", "selector": selector}
            return {"type": "error", "error": "No text or selector provided"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def type_in_web_element(self, text: str, field_placeholder: str = None,
                             field_label: str = None, selector: str = None) -> dict:
        """Type text into a web input field."""
        if not self._driver:
            return {"type": "error", "error": "Browser not open."}
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            wait = WebDriverWait(self._driver, 10)
            el = None

            if field_placeholder:
                el = wait.until(EC.presence_of_element_located(
                    (By.XPATH, f"//input[@placeholder='{field_placeholder}']")))
            elif field_label:
                el = wait.until(EC.presence_of_element_located(
                    (By.XPATH, f"//input[@aria-label='{field_label}'] | //textarea[@aria-label='{field_label}']")))
            elif selector:
                el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

            if el:
                el.clear()
                el.send_keys(text)
                return {"type": "web_typed", "text": text[:40]}
            return {"type": "error", "error": "Web input field not found"}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def read_page_text(self, max_chars: int = 2000) -> dict:
        """Read the visible text content of the current page."""
        if not self._driver:
            return {"type": "error", "error": "Browser not open."}
        try:
            from selenium.webdriver.common.by import By
            body = self._driver.find_element(By.TAG_NAME, "body")
            text = body.text[:max_chars]
            return {"type": "page_text", "text": text, "url": self._driver.current_url}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def navigate(self, url: str) -> dict:
        if not self._driver:
            return {"type": "error", "error": "Browser not open."}
        try:
            self._driver.get(url)
            time.sleep(1)
            return {"type": "navigated", "url": url, "title": self._driver.title}
        except Exception as exc:
            return {"type": "error", "error": str(exc)}

    def close(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None


# ══════════════════════════════════════════════════════════════════════════════
#  App Discovery (Windows Registry + running processes)
# ══════════════════════════════════════════════════════════════════════════════

class AppDiscovery:
    """Discover installed apps and their capabilities on Windows."""

    def __init__(self):
        self._cache = {}

    def get_running_apps(self) -> list:
        """Return list of currently running app windows."""
        try:
            import psutil
            apps = []
            seen = set()
            for proc in psutil.process_iter(["name", "pid", "exe"]):
                try:
                    name = proc.info["name"]
                    if name and name not in seen and name.endswith(".exe"):
                        seen.add(name)
                        apps.append({
                            "name": name,
                            "pid": proc.info["pid"],
                            "exe": proc.info.get("exe", ""),
                        })
                except Exception:
                    pass
            return sorted(apps, key=lambda x: x["name"])
        except Exception as exc:
            logger.warning("Process list error: %s", exc)
            return []

    def find_app_by_keyword(self, keyword: str) -> Optional[dict]:
        """Find a running app that matches a keyword."""
        keyword = keyword.lower()
        for app in self.get_running_apps():
            if keyword in app["name"].lower():
                return app
        return None

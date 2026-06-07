"""
core/brain.py — JARVIS OMEGA V3 Brain
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES vs V2:
  ✅ Groq key checked clearly with helpful error
  ✅ Self-improvement: AI can learn to search/open apps
  ✅ generate_image result properly returned for GUI display
  ✅ Better action dispatch for multi-step tasks
  ✅ install_skill action works
"""

import json
import re
import threading
import logging
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("JARVIS.BRAIN")

try:
    from groq import Groq as GroqClient
    GROQ_AVAILABLE = True
except ImportError:
    GroqClient = None
    GROQ_AVAILABLE = False


SYSTEM_PROMPT = """You are J.A.R.V.I.S — an ultra-advanced AI Operating System assistant for {user_name}.
You are NOT a chatbot. You are an autonomous AI integrated into the computer itself.
You can control hardware, write and run code, search the web, manage files, control apps, and more.

RESPONSE RULES:
1. Natural conversation → reply in plain text (concise, witty, professional).
2. Computer actions → reply ONLY with valid JSON:
   {{"action": "ACTION", "params": {{...}}, "message": "brief user message", "agent": "AGENT_NAME"}}

AVAILABLE ACTIONS:
open_app        → {{"app": "chrome|notepad|vscode|spotify|calculator|explorer|..."}}
close_app       → {{"app": "name"}}
web_search      → {{"query": "search terms"}}
type_text       → {{"text": "text", "press_enter": false, "delay": 1.5}}
click_at        → {{"x": 100, "y": 200, "button": "left"}}
screenshot      → {{"path": "data/screenshots/shot.png"}}
read_screen     → {{}}
find_on_screen  → {{"text": "Search"}}
run_code        → {{"code": "python code", "language": "python", "save_as": "optional.py"}}
create_file     → {{"path": "filename.py", "content": "file content"}}
save_file       → {{"filename": "output.txt", "content": "text", "folder": ""}}
create_project  → {{"name": "project_name", "type": "python|web|arduino|mobile", "description": "..."}}
move_mouse      → {{"x": 100, "y": 200}}
scroll          → {{"direction": "up|down", "amount": 3}}
hotkey          → {{"keys": "ctrl+c"}}
system_cmd      → {{"command": "shell command"}}
set_volume      → {{"level": 50}}
open_url        → {{"url": "https://..."}}
arduino_upload  → {{"code": "arduino code", "port": "auto"}}
arduino_monitor → {{"port": "auto", "baud": 9600}}
generate_image  → {{"prompt": "description", "style": "photorealistic|anime|3d|concept"}}
multi_step      → {{"steps": [{{"action": "...", "params": {{...}}}}, ...]}}
remember        → {{"fact": "thing to remember"}}
set_reminder    → {{"text": "reminder", "minutes": 30}}
system_info     → {{}}
install_skill   → {{"skill": "selenium|pywinauto|psutil|whisper|groq|..."}}

APP CONTROL WORKFLOW (when user says "open X and search Y"):
Step 1: open_app → {{"app": "chrome"}}
Step 2: read_screen → {{}} (to see what's visible)
Step 3: find_on_screen → {{"text": "Search"}} (find the search bar)
Step 4: click_at → {{"x": found_x, "y": found_y}}
Step 5: type_text → {{"text": "Y", "press_enter": true}}

SELF IMPROVEMENT: If user asks you to "learn to do X" or "make yourself able to do Y":
- Use install_skill to install needed packages
- Use run_code to test capabilities
- Use create_file to save new tools

SECURITY: Never bypass CAPTCHAs. Never delete system files. Always confirm destructive operations.
LANGUAGE: Match the user's language (Hindi, English, Hinglish).
Always be concise, smart, and feel like a real AI OS assistant."""


FREE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "llama3-8b-8192",
    "gemma2-9b-it",
]


class JarvisOmegaBrain:
    """Central cognitive engine."""

    def __init__(self, settings: dict, gui_callback: Optional[Callable] = None):
        self.settings     = settings
        self.gui_callback = gui_callback
        self.conversation: list[dict] = []
        self._model  = settings.get("groq_model", "llama-3.3-70b-versatile")
        self._lock   = threading.Lock()

        api_key = settings.get("groq_api_key", "").strip()
        self.groq   = None
        self._has_key = bool(api_key)

        if GROQ_AVAILABLE and api_key:
            try:
                import httpx
                self.groq = GroqClient(
                    api_key=api_key,
                    timeout=20.0,
                    max_retries=1,
                    http_client=httpx.Client(timeout=20.0),
                )
                logger.info("Groq client initialized.")
            except Exception:
                try:
                    self.groq = GroqClient(api_key=api_key, timeout=20.0, max_retries=1)
                except Exception as exc:
                    logger.error("Groq init failed: %s", exc)
        elif not GROQ_AVAILABLE:
            logger.warning("groq package not installed. Run: pip install groq")
        else:
            logger.warning("No Groq API key in config/settings.json")

        from core.memory  import MemoryEngine
        from core.context import ContextAnalyzer
        from tools.tool_manager import ToolManager

        self.memory  = MemoryEngine()
        self.context = ContextAnalyzer()
        self.tools   = ToolManager(settings=settings, gui_callback=gui_callback)

        self._system_prompt = SYSTEM_PROMPT.format(
            user_name=settings.get("user_name", "Sir")
        )
        logger.info("JARVIS OMEGA Brain initialized.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(self, user_input: str) -> str:
        try:
            ctx     = self.context.analyze(user_input, self.conversation)
            mem_ctx = self.memory.recall(user_input)

            full_prompt = user_input
            if mem_ctx:
                full_prompt = f"{user_input}\n[Memory: {mem_ctx}]"

            self.conversation.append({"role": "user", "content": full_prompt})
            raw = self._call_groq()
            self.conversation.append({"role": "assistant", "content": raw})
            self.memory.store(user_input, raw)

            # Trim conversation (keep last 40 turns)
            if len(self.conversation) > 80:
                self.conversation = self.conversation[-80:]

            return self._dispatch(raw)

        except Exception as exc:
            logger.error("Brain.process error: %s", exc, exc_info=True)
            return f"I encountered an error: {exc}"

    def reset(self):
        self.conversation = []

    def set_fast_mode(self, enabled: bool):
        self._model = "llama3-8b-8192" if enabled else self.settings.get("groq_model", "llama-3.3-70b-versatile")

    # ── LLM ───────────────────────────────────────────────────────────────────

    def _call_groq(self) -> str:
        if not self.groq:
            if not GROQ_AVAILABLE:
                return ("⚠️ Groq package not installed!\n"
                        "Run: pip install groq\n"
                        "Then restart JARVIS.")
            if not self._has_key:
                return ("⚠️ No Groq API key configured!\n"
                        "1. Get your FREE key at: https://console.groq.com\n"
                        "2. Click ⚙ Settings in JARVIS\n"
                        "3. Paste your key in 'Groq API Key' field\n"
                        "4. Click Save")
            return "⚠️ Groq client failed to initialize. Check your API key."

        messages = [{"role": "system", "content": self._system_prompt}] + self.conversation

        for model in [self._model] + [m for m in FREE_MODELS if m != self._model]:
            try:
                resp = self.groq.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=self.settings.get("temperature", 0.7),
                    max_tokens=self.settings.get("max_tokens", 2048),
                )
                return resp.choices[0].message.content
            except Exception as exc:
                err_str = str(exc).lower()
                if any(k in err_str for k in ("connection", "network", "timeout",
                                               "unreachable", "refused")):
                    return ("⚠️ Cannot reach Groq servers.\n"
                            "Check your internet connection and try again.")
                if "invalid api key" in err_str or "authentication" in err_str:
                    return ("⚠️ Invalid Groq API key!\n"
                            "Get a free key at console.groq.com and update in ⚙ Settings.")
                logger.warning("Model %s failed: %s — trying next", model, exc)
                continue

        return "All AI models unavailable. Check your Groq API key at console.groq.com"

    def _call_groq_raw(self, prompt: str) -> str:
        if not self.groq:
            return ""
        try:
            resp = self.groq.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            return resp.choices[0].message.content
        except Exception as exc:
            logger.warning("Raw Groq call failed: %s", exc)
            return ""

    # ── Dispatch ───────────────────────────────────────────────────────────────

    def _dispatch(self, raw: str) -> str:
        action_data = self._extract_json(raw)
        if not action_data:
            return raw

        action  = action_data.get("action", "")
        params  = action_data.get("params", {})
        message = action_data.get("message", "")

        if not action:
            return raw

        # Security gate
        if self._is_dangerous(action, params):
            return "⚠️ Security: That operation was blocked for safety."

        # Multi-step
        if action == "multi_step":
            return self._run_multi_step(params.get("steps", []), message)

        # Create project
        if action == "create_project":
            from tools.code_tools import create_project_scaffold
            result = create_project_scaffold(params.get("name", "project"), params.get("type", "python"), params.get("description", ""))
            if self.gui_callback and result:
                self.gui_callback("tool_result", action, result)
            return message or result.get("summary", "Project created.")

        # Remember
        if action == "remember":
            self.memory.store_fact(params.get("fact", ""))
            return message or "Got it, I'll remember that."

        # Set reminder
        if action == "set_reminder":
            self._schedule_reminder(params.get("text", ""), params.get("minutes", 5))
            return message or f"Reminder set for {params.get('minutes', 5)} minutes."

        # System info
        if action == "system_info":
            from tools.system_tools import get_system_info
            return self._format_sysinfo(get_system_info())

        # Generic tool dispatch
        result = self.tools.execute(action, params)
        if result and self.gui_callback:
            self.gui_callback("tool_result", action, result)

        # Format result for user
        if isinstance(result, dict):
            rtype = result.get("type", "")
            if rtype == "web_results":
                return self._format_web(result, message)
            if rtype == "code_result":
                stdout = result.get("stdout", "")
                return message or (f"Code executed.\n{stdout[:500]}" if stdout else "Code ran successfully.")
            if rtype == "image":
                # Return message + URL for GUI to display
                path = result.get("path", "")
                url  = result.get("url", "")
                if path:
                    return f"{message or 'Here is your generated image:'}\n[IMAGE:{path}]\nURL: {url}"
                elif url:
                    return f"{message or 'Image generated:'}\nURL: {url}\n(Open in browser to view)"
            if rtype == "skill_installed":
                return result.get("message", "Skill installed.")
            if rtype == "file_created":
                return message or f"✅ File created: {result.get('path', '')}"
            if rtype == "file_saved":
                return message or f"✅ File saved: {result.get('path', '')}"
            if rtype == "app_opened":
                return message or f"✅ Opened {params.get('app', '')}"
            if rtype == "error":
                return f"⚠️ {result.get('error', 'Unknown error')}"
            if rtype == "screen_read":
                text = result.get("text", "")
                words = result.get("words", [])
                words_summary = ""
                if words:
                    sample = [w["text"] for w in words[:10]]
                    words_summary = f"\nDetected text on screen: {', '.join(sample)}"
                return message or f"Screen read complete.{words_summary}\n{text[:300]}"

        return message or raw

    def _run_multi_step(self, steps: list, message: str) -> str:
        results = []
        screen_data = None
        for i, step in enumerate(steps, 1):
            s_action = step.get("action", "")
            s_params = step.get("params", {})
            if not s_action:
                continue
            if self._is_dangerous(s_action, s_params):
                results.append(f"Step {i} blocked: dangerous action")
                continue

            # If we have screen data from a previous read_screen, inject coords
            if screen_data and s_action == "click_at":
                words = screen_data.get("words", [])
                target = s_params.get("find_text", "")
                if target:
                    for w in words:
                        if target.lower() in w["text"].lower():
                            s_params["x"] = w["x"]
                            s_params["y"] = w["y"]
                            break

            result = self.tools.execute(s_action, s_params)
            if result and self.gui_callback:
                self.gui_callback("tool_result", s_action, result)

            # Save screen data for next steps to use
            if result and result.get("type") == "screen_read":
                screen_data = result

            results.append(f"Step {i} ({s_action}): done")
            time.sleep(0.4)

        return message or f"Completed {len(steps)} steps: " + ", ".join(results)

    def _schedule_reminder(self, text: str, minutes: int):
        def _remind():
            time.sleep(minutes * 60)
            if self.gui_callback:
                self.gui_callback("reminder", "reminder", {"text": text})
        threading.Thread(target=_remind, daemon=True).start()

    def _is_dangerous(self, action: str, params: dict) -> bool:
        DANGEROUS = {
            "system_cmd": ["rm -rf", "format", "del /f /s", "rd /s /q", "shutdown /f", "mkfs"],
            "run_code":   ["os.remove", "shutil.rmtree", "open('/etc", "open('C:\\\\Windows"],
        }
        checks  = DANGEROUS.get(action, [])
        content = str(params).lower()
        return any(p.lower() in content for p in checks)

    def _format_web(self, result: dict, message: str) -> str:
        results = result.get("results", [])
        if not results:
            return message or "No results found."
        lines = [message or "Here's what I found:"]
        for i, r in enumerate(results[:5], 1):
            lines.append(f"\n{i}. {r.get('title', '')}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet'][:160]}")
            if r.get("url"):
                lines.append(f"   🔗 {r['url'][:80]}")
        return "\n".join(lines)

    def _format_sysinfo(self, info: dict) -> str:
        lines = ["📊 System Status:"]
        lines.append(f"  CPU: {info.get('cpu_percent', 0):.1f}%")
        lines.append(f"  RAM: {info.get('ram_used', 0):.1f} / {info.get('ram_total', 0):.1f} GB")
        lines.append(f"  Disk: {info.get('disk_free', 0):.1f} GB free")
        lines.append(f"  Battery: {info.get('battery', 'N/A')}")
        lines.append(f"  Network: {'✅ Online' if info.get('online') else '❌ Offline'}")
        return "\n".join(lines)

    def _extract_json(self, text: str) -> Optional[dict]:
        text = text.strip()
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        match = re.search(r'\{[^{}]*"action"\s*:[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        try:
            start = text.index("{")
            depth, end = 0, -1
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass
        return None

"""
core/brain.py
─────────────
JARVIS OMEGA Brain — Multi-Agent Architecture
Free via Groq API (llama-3.3-70b-versatile)

Agents:
  PlannerAgent  — breaks goals into subtasks
  ResearchAgent — web search & knowledge gathering
  CodingAgent   — generates, debugs, refactors code
  VisionAgent   — reads screens, OCR
  AutomationAgent — controls computer
  MemoryAgent   — stores and recalls information
  DeviceAgent   — Arduino / hardware control
  SecurityAgent — validates dangerous actions
"""

import json
import re
import threading
import logging
import time
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger("JARVIS.BRAIN")

# ── Groq client ───────────────────────────────────────────────────────────────
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
run_code        → {{"code": "python code", "language": "python", "save_as": "optional_filename.py"}}
create_file     → {{"path": "filename.py", "content": "file content here"}}
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
install_skill   → {{"skill": "blender|arduino|unity|photoshop"}}

SECURITY: Never bypass CAPTCHAs. Never delete system files. Always confirm destructive operations.

MULTI-STEP EXAMPLE:
"Create a snake game in Python and run it" →
{{"action": "create_project", "params": {{"name": "snake_game", "type": "python", "description": "snake game using pygame"}}, "message": "Creating a Snake game project...", "agent": "CodingAgent"}}

LANGUAGE: Match the user's language (Hindi, English, Hinglish).
Always be concise, smart, and feel like a real AI OS assistant."""


FREE_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "llama3-8b-8192",
    "gemma2-9b-it",
]


class Agent:
    """Base agent class."""
    name = "BaseAgent"
    
    def __init__(self, brain: "JarvisOmegaBrain"):
        self.brain = brain
    
    def can_handle(self, action: str) -> bool:
        return False
    
    def execute(self, action: str, params: dict) -> dict:
        return {"type": "error", "error": f"{self.name} cannot handle {action}"}


class SecurityAgent(Agent):
    """Validates and gates dangerous actions."""
    name = "SecurityAgent"
    
    DANGEROUS = {
        "system_cmd": ["rm -rf", "format", "del /f /s", "rd /s /q", "shutdown", "mkfs"],
        "run_code": [
            "os.remove", "shutil.rmtree",
            "subprocess.call",
            "open('/etc", "open('C:\\\\Windows",
        ],
    }
    
    def validate(self, action: str, params: dict, callback: Optional[Callable] = None) -> tuple[bool, str]:
        """Returns (allowed, reason)."""
        checks = self.DANGEROUS.get(action, [])
        content = str(params)
        for pattern in checks:
            if pattern.lower() in content.lower():
                msg = f"⚠️ Security: This action contains potentially dangerous operation: '{pattern}'. Blocked."
                logger.warning("SecurityAgent blocked: %s in %s", pattern, action)
                return False, msg
        return True, ""


class PlannerAgent(Agent):
    """Breaks complex goals into subtasks."""
    name = "PlannerAgent"
    
    def plan(self, goal: str, brain: "JarvisOmegaBrain") -> list[dict]:
        """Use LLM to decompose a complex goal into steps."""
        plan_prompt = f"""Break this goal into 2-6 concrete steps for a computer AI assistant.
Goal: {goal}
Return ONLY a JSON array: [{{"step": 1, "action": "...", "description": "..."}}]
Each action must be one of: open_app, web_search, run_code, create_file, type_text, system_cmd, screenshot"""
        
        result = brain._call_groq_raw(plan_prompt)
        try:
            match = re.search(r'\[.*\]', result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return []


class ResearchAgent(Agent):
    """Handles web research and knowledge gathering."""
    name = "ResearchAgent"
    
    def can_handle(self, action: str) -> bool:
        return action == "web_search"
    
    def search(self, query: str) -> dict:
        from tools.web_tools import web_search
        return web_search(query)


class CodingAgent(Agent):
    """Generates, debugs and runs code."""
    name = "CodingAgent"
    
    def can_handle(self, action: str) -> bool:
        return action in ("run_code", "create_file", "create_project")
    
    def create_project(self, name: str, proj_type: str, description: str) -> dict:
        from tools.code_tools import create_project_scaffold
        return create_project_scaffold(name, proj_type, description)


class VisionAgent(Agent):
    """Reads and understands the screen."""
    name = "VisionAgent"
    
    def can_handle(self, action: str) -> bool:
        return action in ("screenshot", "read_screen")
    
    def read_screen(self) -> dict:
        from tools.vision_tools import capture_and_read
        return capture_and_read()


class AutomationAgent(Agent):
    """Controls the computer."""
    name = "AutomationAgent"
    
    def can_handle(self, action: str) -> bool:
        return action in ("click_at", "move_mouse", "type_text", "hotkey",
                          "scroll", "open_app", "close_app")


class DeviceAgent(Agent):
    """Controls Arduino and hardware."""
    name = "DeviceAgent"
    
    def can_handle(self, action: str) -> bool:
        return action in ("arduino_upload", "arduino_monitor")


class MemoryAgentClass(Agent):
    """Manages persistent memory."""
    name = "MemoryAgent"
    
    def can_handle(self, action: str) -> bool:
        return action == "remember"


# ══════════════════════════════════════════════════════════════════════════════
#  JARVIS OMEGA Brain
# ══════════════════════════════════════════════════════════════════════════════

class JarvisOmegaBrain:
    """Central cognitive engine with multi-agent architecture."""

    def __init__(self, settings: dict, gui_callback: Optional[Callable] = None):
        self.settings = settings
        self.gui_callback = gui_callback
        self.conversation: list[dict] = []
        self._model = settings.get("groq_model", "llama-3.3-70b-versatile")
        self._lock = threading.Lock()
        self._reminders: list[dict] = []

        # Groq client — timeout + max 1 retry so connection errors fail fast
        api_key = settings.get("groq_api_key", "").strip()
        if GROQ_AVAILABLE and api_key:
            try:
                import httpx
                self.groq = GroqClient(
                    api_key=api_key,
                    timeout=15.0,
                    max_retries=1,
                    http_client=httpx.Client(timeout=15.0),
                )
            except Exception:
                try:
                    self.groq = GroqClient(api_key=api_key, timeout=15.0, max_retries=1)
                except Exception:
                    self.groq = GroqClient(api_key=api_key)
        else:
            self.groq = None

        # Load sub-systems
        from core.memory import MemoryEngine
        from core.context import ContextAnalyzer
        from tools.tool_manager import ToolManager

        self.memory = MemoryEngine()
        self.context = ContextAnalyzer()
        self.tools = ToolManager(settings=settings, gui_callback=gui_callback)

        # Agents
        self.security = SecurityAgent(self)
        self.planner = PlannerAgent(self)
        self.researcher = ResearchAgent(self)
        self.coder = CodingAgent(self)
        self.vision = VisionAgent(self)
        self.automation = AutomationAgent(self)
        self.device = DeviceAgent(self)
        self.mem_agent = MemoryAgentClass(self)

        self._system_prompt = SYSTEM_PROMPT.format(
            user_name=settings.get("user_name", "Sir")
        )
        logger.info("JARVIS OMEGA Brain initialized with multi-agent architecture.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(self, user_input: str, mode: str = "chat") -> str:
        """Full pipeline: context → memory → agents → LLM → execute → reply."""
        try:
            # Context analysis
            ctx = self.context.analyze(user_input, self.conversation)
            mem_ctx = self.memory.recall(user_input)

            # Build prompt
            full_prompt = user_input
            if mem_ctx:
                full_prompt = f"{user_input}\n[Memory: {mem_ctx}]"

            self.conversation.append({"role": "user", "content": full_prompt})

            # LLM call
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

    def process_async(self, user_input: str, callback: Callable):
        """Process in background thread, call callback with result."""
        def _run():
            result = self.process(user_input)
            callback(result)
        threading.Thread(target=_run, daemon=True).start()

    def reset(self):
        self.conversation = []

    def set_fast_mode(self, enabled: bool):
        self._model = "llama3-8b-8192" if enabled else self.settings.get("groq_model", "llama-3.3-70b-versatile")

    # ── LLM call ───────────────────────────────────────────────────────────────

    def _call_groq(self) -> str:
        if not self.groq:
            return ("⚠️ No Groq API key configured!\n"
                    "Get your FREE key at console.groq.com\n"
                    "Add to config/settings.json → groq_api_key")

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
                # If it is a connection/network error, stop immediately — no point
                # trying other models if there is no internet.
                if any(k in err_str for k in ("connection", "network", "connect",
                                               "timeout", "unreachable", "refused")):
                    logger.warning("Network error — stopping model fallback: %s", exc)
                    return ("⚠️ Cannot reach Groq servers.
"
                            "Check your internet connection or try again in a moment.")
                logger.warning("Model %s failed: %s — trying next", model, exc)
                continue

        return "All AI models unavailable. Check your Groq API key at console.groq.com"

    def _call_groq_raw(self, prompt: str) -> str:
        """One-shot call without conversation history."""
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
        """Parse JSON action and dispatch to correct agent/tool."""
        action_data = self._extract_json(raw)
        if not action_data:
            return raw  # Plain text reply

        action  = action_data.get("action", "")
        params  = action_data.get("params", {})
        message = action_data.get("message", "")

        if not action:
            return raw

        # Security gate
        allowed, reason = self.security.validate(action, params, self.gui_callback)
        if not allowed:
            return reason

        # Multi-step
        if action == "multi_step":
            return self._run_multi_step(params.get("steps", []), message)

        # Create project (CodingAgent)
        if action == "create_project":
            result = self.coder.create_project(
                params.get("name", "project"),
                params.get("type", "python"),
                params.get("description", ""),
            )
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
            info = get_system_info()
            return self._format_sysinfo(info)

        # Generic tool dispatch
        result = self.tools.execute(action, params)

        if result and self.gui_callback:
            self.gui_callback("tool_result", action, result)

        # Format results
        if isinstance(result, dict):
            if result.get("type") == "web_results":
                return self._format_web(result, message)
            if result.get("type") == "code_result":
                return message or f"Code executed. Output: {result.get('stdout', '')[:200]}"
            if result.get("type") == "project_created":
                return message or f"Project created at: {result.get('path', '')}"
            if result.get("type") == "error":
                return f"⚠️ {result.get('error', 'Unknown error')}"

        return message or raw

    def _run_multi_step(self, steps: list, message: str) -> str:
        results = []
        for i, step in enumerate(steps, 1):
            s_action = step.get("action", "")
            s_params = step.get("params", {})
            if not s_action:
                continue
            allowed, reason = self.security.validate(s_action, s_params)
            if not allowed:
                results.append(f"Step {i} blocked: {reason}")
                continue
            result = self.tools.execute(s_action, s_params)
            if result and self.gui_callback:
                self.gui_callback("tool_result", s_action, result)
            results.append(f"Step {i} ({s_action}): done")
            time.sleep(0.3)
        return message or f"Completed {len(steps)} steps: " + ", ".join(results)

    def _schedule_reminder(self, text: str, minutes: int):
        def _remind():
            time.sleep(minutes * 60)
            if self.gui_callback:
                self.gui_callback("reminder", "reminder", {"text": text})
        threading.Thread(target=_remind, daemon=True).start()

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
        # Direct JSON
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        # Find JSON with action key
        match = re.search(r'\{[^{}]*"action"\s*:[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Nested JSON (multi_step)
        try:
            start = text.index('{')
            depth, end = 0, -1
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            if end > start:
                return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass
        return None

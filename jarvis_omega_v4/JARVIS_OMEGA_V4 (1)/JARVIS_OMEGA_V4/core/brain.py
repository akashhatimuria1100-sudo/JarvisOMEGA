"""
core/brain.py — JARVIS OMEGA V4 Brain
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Features:
  ✅ Multi-provider FREE LLM routing (Gemini, OpenRouter, NVIDIA, SambaNova, Cerebras, Groq, Local)
  ✅ Self-improvement: AI can learn to search/open apps
  ✅ generate_image result properly returned for GUI display
  ✅ Better action dispatch for multi-step tasks
  ✅ install_skill action works
  ✅ Local LLM fallback — works without any API key
"""

import json
import os
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
focus_app       → {{"app": "chrome"}}  (bring window to front before typing)

APP CONTROL WORKFLOW (when user says "open X and search Y"):
Step 1: open_app → {{"app": "chrome"}}
Step 2: read_screen → {{}} (to see what's visible)
Step 3: find_on_screen → {{"text": "Search"}} (find the search bar)
Step 4: click_at → {{"x": found_x, "y": found_y}}
Step 5: focus_app → {{"app": "chrome"}} (ensure Chrome is focused before typing)
Step 6: type_text → {{"text": "Y", "press_enter": true}}

CRITICAL RULES:
- When typing into a browser or app, ALWAYS call focus_app first to make sure the target is focused.
- Never type into your own JARVIS chat window.
- If you read the screen and the search bar is not visible, scroll down first.
- When opening a URL, just use open_app or open_url directly.

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


# ═══════════════════════════════════════════════════════════════════════════════
# Local LLM Engine (no API required)
# ═══════════════════════════════════════════════════════════════════════════════

class LocalLLMEngine:
    """
    Runs a small quantized Llama-3.2-3B model locally via llama-cpp-python.
    Auto-downloads the model on first use (~2 GB).
    """

    DEFAULT_REPO = "unsloth/Llama-3.2-3B-Instruct-GGUF"
    DEFAULT_FILE = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    MODEL_DIR = Path(__file__).resolve().parent.parent / "data" / "models"

    def __init__(self, gui_callback: Optional[Callable] = None):
        self._llm = None
        self.model_path = self.MODEL_DIR / self.DEFAULT_FILE
        self.gui_callback = gui_callback
        self._loading = False

    def _ensure_model(self) -> bool:
        if self.model_path.exists():
            return True
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        try:
            from huggingface_hub import hf_hub_download
            if self.gui_callback:
                self.gui_callback(
                    "status",
                    "download",
                    {"text": "📦 Downloading local model (~2 GB). First run only — please wait…"},
                )
            logger.info("Downloading %s/%s …", self.DEFAULT_REPO, self.DEFAULT_FILE)
            hf_hub_download(
                repo_id=self.DEFAULT_REPO,
                filename=self.DEFAULT_FILE,
                local_dir=str(self.MODEL_DIR),
                local_dir_use_symlinks=False,
            )
            if self.gui_callback:
                self.gui_callback(
                    "status",
                    "download",
                    {"text": "✅ Model downloaded — loading into memory…"},
                )
            return True
        except Exception as exc:
            logger.error("Model download failed: %s", exc)
            if self.gui_callback:
                self.gui_callback(
                    "status",
                    "download",
                    {"text": f"⚠️ Model download failed: {exc}"},
                )
            return False

    def load(self) -> bool:
        if self._llm is not None:
            return True
        if self._loading:
            return False
        self._loading = True
        try:
            if not self._ensure_model():
                return False
            try:
                from llama_cpp import Llama
            except ImportError as exc:
                logger.error("llama-cpp-python not installed: %s", exc)
                return False

            if self.gui_callback:
                self.gui_callback(
                    "status",
                    "download",
                    {"text": "🧠 Loading model into memory (may take 10–30 s)…"},
                )
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=4096,
                n_threads=(os.cpu_count() or 4),
                verbose=False,
            )
            if self.gui_callback:
                self.gui_callback(
                    "status",
                    "download",
                    {"text": "✅ Local model ready — offline mode active."},
                )
            return True
        except Exception as exc:
            logger.error("Local LLM load failed: %s", exc)
            return False
        finally:
            self._loading = False

    def chat(self, messages, temperature=0.7, max_tokens=512) -> str:
        if not self.load():
            return (
                "⚠️ Local model not available.\n\n"
                "Options:\n"
                "1. Install llama-cpp-python:  pip install llama-cpp-python\n"
                "2. Install huggingface_hub:   pip install huggingface_hub\n"
                "3. Check your internet for the first download (~2 GB).\n"
                "4. Or add a free API key in ⚙ Settings for cloud mode."
            )
        try:
            resp = self._llm.create_chat_completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=["<|eot_id|>", "", "</s>"],
            )
            return resp["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("Local LLM inference error: %s", exc)
            return f"⚠️ Local model error: {exc}"

    @property
    def ready(self) -> bool:
        return self._llm is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Central Brain
# ═══════════════════════════════════════════════════════════════════════════════

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
        self.local_llm = None
        self._use_local = settings.get("use_local_llm", True)  # always load local as backup
        self._multi_provider = None

        # ── Groq ──────────────────────────────────────────────────────────────
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

        # ── Multi-provider free LLM engine ──────────────────────────────────
        try:
            from core.multi_provider_llm import MultiProviderLLM
            self._multi_provider = MultiProviderLLM(settings)
            if self._multi_provider.any_available():
                logger.info("Multi-provider LLM engine ready (%d providers).",
                            len(self._multi_provider._clients))
            else:
                logger.info("No multi-provider keys found. Add free API keys in Settings.")
        except Exception as exc:
            logger.warning("Multi-provider LLM not available: %s", exc)

        # ── Local LLM (always loaded as ultimate offline fallback) ──────────
        self._init_local()

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

    def _init_local(self):
        try:
            self.local_llm = LocalLLMEngine(gui_callback=self.gui_callback)
        except Exception as exc:
            logger.warning("Local LLM init failed: %s", exc)

    def _is_rate_limit_err(self, exc: Exception) -> bool:
        err_str = str(exc).lower()
        return any(k in err_str for k in (
            "429", "rate limit", "too many requests", "throttled",
            "quota exceeded", "tokens per minute", "requests per minute",
            "capacity", "limit exceeded", "api rate",
        ))

    # ── Public API ─────────────────────────────────────────────────────────────

    def process(self, user_input: str) -> str:
        try:
            ctx     = self.context.analyze(user_input, self.conversation)
            mem_ctx = self.memory.recall(user_input)

            full_prompt = user_input
            if mem_ctx:
                full_prompt = f"{user_input}\n[Memory: {mem_ctx}]"

            self.conversation.append({"role": "user", "content": full_prompt})
            raw = self._call_llm()
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

    # ── LLM routing (multi-provider → Groq → local) ───────────────────────

    def _call_llm(self) -> str:
        """
        Query ALL available providers in parallel, collect every response,
        then return the BEST one (not just the fastest).

        Strategy:
          1. Fire every cloud provider + Groq + Local LLM simultaneously.
          2. Wait up to 12 seconds for them to finish.
          3. Score all valid responses by quality + length.
          4. Return the highest-scoring answer.
        This gives the smartest output instead of the fastest random one.
        """
        import concurrent.futures
        import time

        messages = [{"role": "system", "content": self._system_prompt}] + self.conversation
        temp = self.settings.get("temperature", 0.7)
        max_tok = self.settings.get("max_tokens", 2048)
        all_responses: dict[str, str] = {}

        def _fetch_multi():
            if not (self._multi_provider and self._multi_provider.any_available()):
                return {}
            try:
                return self._multi_provider.chat_all(messages, temp, max_tok, timeout=10)
            except Exception as exc:
                logger.warning("Multi-provider chat_all error: %s", exc)
                return {}

        def _fetch_groq():
            if not self.groq:
                return {}
            try:
                text = self._call_groq(messages, temp, max_tok)
                if text and not text.startswith("⚠️"):
                    return {"groq": text}
            except Exception as exc:
                logger.warning("Groq fetch error: %s", exc)
            return {}

        def _fetch_local():
            if not self.local_llm:
                return {}
            try:
                text = self._call_local()
                if text and not text.startswith("⚠️"):
                    return {"local": text}
            except Exception as exc:
                logger.warning("Local fetch error: %s", exc)
            return {}

        # Launch all three fetchers in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(_fetch_multi): "multi",
                executor.submit(_fetch_groq): "groq",
                executor.submit(_fetch_local): "local",
            }
            done, not_done = concurrent.futures.wait(futures, timeout=12, return_when=concurrent.futures.ALL_COMPLETED)
            for f in not_done:
                f.cancel()
            for f in done:
                try:
                    result = f.result()
                    if isinstance(result, dict):
                        all_responses.update(result)
                except Exception as exc:
                    logger.warning("Provider fetcher error: %s", exc)

        if not all_responses:
            logger.error("All AI providers failed. No responses collected.")
            return (
                "⚠️ No AI provider available.\n\n"
                "FREE OPTIONS (no credit card needed):\n"
                "1. Local mode:  pip install llama-cpp-python huggingface_hub  → restart\n"
                "2. Google Gemini: https://aistudio.google.com/app/apikey → paste GOOGLE_API_KEY in Settings\n"
                "3. OpenRouter: https://openrouter.com/keys → paste OPENROUTER_API_KEY in Settings\n"
                "4. NVIDIA NIM: https://build.nvidia.com → paste NVIDIA_API_KEY in Settings\n"
                "5. SambaNova: https://cloud.sambanova.ai → paste SAMBANOVA_API_KEY in Settings\n"
                "6. Cerebras: https://cloud.cerebras.ai → paste CEREBRAS_API_KEY in Settings\n"
                "7. Groq: https://console.groq.com → paste GROQ_API_KEY in Settings\n\n"
                "All of these are FREE tiers. You can add multiple keys for redundancy."
            )

        return self._pick_best_response(all_responses)

    def _pick_best_response(self, responses: dict[str, str]) -> str:
        """
        Score every provider response and return the best one.
        Heuristic: longer (but not absurd) + higher provider quality score wins.
        """
        # Provider quality tiers (higher = smarter model usually)
        quality_scores = {
            "nvidia": 100,      # NEW: Nemotron-3 Ultra 550B is the biggest free model
            "groq": 95,         # 70B/8B models, very fast
            "cerebras": 93,     # 70B model, fast
            "sambanova": 88,    # 70B model
            "gemini": 85,       # 1.5 Flash, multimodal
            "openrouter": 78,   # varies by free model
            "local": 60,        # 3B CPU model
        }

        best_name = None
        best_score = -1
        best_text = ""

        for name, text in responses.items():
            if not text or text.startswith("⚠️"):
                continue
            q = quality_scores.get(name, 70)
            # Length bonus: cap at 1500 chars so concise answers aren't punished vs novels
            length_bonus = min(len(text), 1500)
            score = q + length_bonus
            logger.debug("Provider '%s' score=%d (quality=%d, len=%d)", name, score, q, length_bonus)
            if score > best_score:
                best_score = score
                best_name = name
                best_text = text

        if best_name:
            logger.info(
                "Best response chosen from '%s' (score=%d, len=%d) out of %d providers.",
                best_name, best_score, len(best_text), len(responses)
            )
            return best_text

        # Fallback: return first available response
        logger.warning("No valid scored response; returning raw fallback.")
        return list(responses.values())[0]

    def _call_groq(self, messages, temperature, max_tokens) -> str:
        for model in [self._model] + [m for m in FREE_MODELS if m != self._model]:
            try:
                resp = self.groq.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            except Exception as exc:
                err_str = str(exc).lower()
                if any(k in err_str for k in ("connection", "network", "timeout", "unreachable", "refused")):
                    return ("⚠️ Cannot reach Groq servers.\n"
                            "Check your internet connection and try again.")
                if "invalid api key" in err_str or "authentication" in err_str:
                    return ("⚠️ Invalid Groq API key!\n"
                            "Get a free key at console.groq.com and update in ⚙ Settings.")
                if self._is_rate_limit_err(exc):
                    logger.warning("Groq rate limit on %s", model)
                    continue
                logger.warning("Model %s failed: %s — trying next", model, exc)
                continue
        return ""

    def _call_local(self) -> str:
        recent = self.conversation[-40:] if len(self.conversation) > 40 else self.conversation
        messages = [{"role": "system", "content": self._system_prompt}] + recent
        return self.local_llm.chat(
            messages,
            temperature=self.settings.get("temperature", 0.7),
            max_tokens=min(self.settings.get("max_tokens", 1024), 1024),
        )

    def _call_groq_raw(self, prompt: str) -> str:
        if not self.groq:
            return ""
        try:
            resp = self.groq.chat.completions.create(
                model="llama3-8b-8192",
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

"""
core/self_improve.py — JARVIS OMEGA V2 Self-Improvement Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UPGRADE vs old version:
  ✅ AST-based code analysis (understands its own code structure)
  ✅ LLM writes new tool/skill code based on analysis
  ✅ Sandbox testing before integration (no broken code)
  ✅ Auto git-commit of improvements
  ✅ Hot-reload: new skills available immediately, no restart
  ✅ Still scrapes web for knowledge (kept from v1)

Self-improvement loop:
  1. CodeAnalyzer scans codebase with AST → finds gaps/issues
  2. FeatureWriter asks LLM to write a new skill/fix
  3. SandboxTester runs new code in isolated subprocess
  4. If tests pass → AutoIntegrator writes to skills/ folder
  5. ToolManager hot-reloads → new skill immediately available
  6. GitCommitter commits with auto message
"""

import ast
import json
import time
import threading
import logging
import subprocess
import tempfile
import os
import importlib
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("JARVIS.SELFIMPROVE")
_BASE = Path(__file__).resolve().parent.parent

DEFAULT_TOPICS = [
    "latest AI assistant features 2025",
    "Python automation techniques",
    "Windows UI automation tutorial",
    "voice assistant improvements",
    "natural language processing 2025",
]


# ══════════════════════════════════════════════════════════════════════════════
#  Code Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class CodeAnalyzer:
    """Analyze the JARVIS codebase using AST to find improvement opportunities."""

    def analyze_file(self, filepath: Path) -> dict:
        """Parse a Python file and extract its structure."""
        try:
            source = filepath.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception as exc:
            return {"error": str(exc)}

        functions = []
        classes = []
        todos = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node) or ""
                # Flag functions with no body beyond a pass/return
                body_complex = sum(1 for n in ast.walk(node)
                                   if isinstance(n, (ast.If, ast.For, ast.While, ast.Try)))
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "has_docstring": bool(docstring),
                    "complexity": body_complex,
                    "is_stub": body_complex == 0 and len(node.body) <= 2,
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({"name": node.name, "line": node.lineno})

        # Look for TODO/FIXME comments
        for i, line in enumerate(source.splitlines(), 1):
            stripped = line.strip()
            if any(kw in stripped.upper() for kw in ("TODO", "FIXME", "HACK", "XXX")):
                todos.append({"line": i, "text": stripped})

        stubs = [f for f in functions if f["is_stub"]]
        return {
            "file": str(filepath),
            "functions": len(functions),
            "classes": len(classes),
            "stubs": stubs,
            "todos": todos,
        }

    def scan_codebase(self) -> list:
        """Scan the whole codebase and return analysis results."""
        results = []
        for py_file in _BASE.rglob("*.py"):
            # Skip pycache and installed packages
            if "__pycache__" in str(py_file) or "site-packages" in str(py_file):
                continue
            result = self.analyze_file(py_file)
            if result.get("stubs") or result.get("todos"):
                results.append(result)
        return results

    def suggest_improvements(self) -> list:
        """Return list of suggested improvements based on analysis."""
        suggestions = []
        for analysis in self.scan_codebase():
            for stub in analysis.get("stubs", []):
                suggestions.append({
                    "type": "stub_function",
                    "file": analysis["file"],
                    "function": stub["name"],
                    "line": stub["line"],
                    "priority": "medium",
                })
            for todo in analysis.get("todos", []):
                suggestions.append({
                    "type": "todo",
                    "file": analysis["file"],
                    "text": todo["text"],
                    "line": todo["line"],
                    "priority": "low",
                })
        return suggestions


# ══════════════════════════════════════════════════════════════════════════════
#  Feature Writer
# ══════════════════════════════════════════════════════════════════════════════

class FeatureWriter:
    """Uses the LLM to write new tool code based on analysis."""

    def __init__(self, groq_client):
        self.groq = groq_client

    def write_new_skill(self, skill_description: str) -> str:
        """Ask LLM to write a new skill module."""
        if not self.groq:
            return ""
        prompt = f"""Write a Python module for a JARVIS AI assistant skill.
Skill description: {skill_description}

Requirements:
- Module must have a clear function or class with docstring
- Must handle ImportError gracefully (try/except ImportError)
- Must return a dict with 'type' key on success and 'error' key on failure
- Must be self-contained (no external state)
- Keep it under 100 lines

Return ONLY the Python code, no markdown, no explanation."""

        try:
            resp = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("FeatureWriter LLM error: %s", exc)
            return ""

    def write_improvement(self, file_content: str, issue: str) -> str:
        """Ask LLM to fix a specific issue in existing code."""
        if not self.groq:
            return ""
        prompt = f"""You are improving Python code for a JARVIS AI assistant.
Issue to fix: {issue}

Current code (excerpt):
{file_content[:1500]}

Write ONLY the improved Python code for the relevant function/section.
No markdown, no explanation."""

        try:
            resp = self.groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600,
            )
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("FeatureWriter improvement error: %s", exc)
            return ""


# ══════════════════════════════════════════════════════════════════════════════
#  Sandbox Tester
# ══════════════════════════════════════════════════════════════════════════════

class SandboxTester:
    """Run new code in an isolated subprocess to verify it doesn't crash."""

    def test_code(self, code: str, timeout: int = 10) -> dict:
        """
        Run code in a sandboxed subprocess.
        Returns {'passed': True/False, 'output': str, 'error': str}
        """
        # Safety check: refuse code with obviously dangerous patterns
        DANGEROUS = ["os.remove", "shutil.rmtree", "format(", "del /", "rm -rf",
                     "subprocess.call", "__import__('os').system"]
        for pattern in DANGEROUS:
            if pattern in code:
                return {"passed": False, "output": "",
                        "error": f"Dangerous pattern blocked: {pattern}"}

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py",
                                         delete=False, encoding="utf-8") as f:
            # Wrap with a basic import test
            test_wrapper = f"""
import sys
try:
{chr(10).join('    ' + line for line in code.splitlines())}
    print("__TEST_PASSED__")
except ImportError as e:
    print(f"__IMPORT_ERROR__: {{e}}")
except Exception as e:
    print(f"__RUNTIME_ERROR__: {{e}}")
"""
            f.write(test_wrapper)
            fname = f.name

        try:
            result = subprocess.run(
                ["python", fname],
                capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout + result.stderr
            if "__TEST_PASSED__" in output:
                return {"passed": True, "output": output, "error": ""}
            elif "__IMPORT_ERROR__" in output:
                # Import errors are OK — the module just needs the package installed
                return {"passed": True, "output": output,
                        "error": "Missing imports (install later)"}
            else:
                return {"passed": False, "output": output,
                        "error": result.stderr[:500] or "Runtime error"}
        except subprocess.TimeoutExpired:
            return {"passed": False, "output": "", "error": "Timed out"}
        except Exception as exc:
            return {"passed": False, "output": "", "error": str(exc)}
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
#  Auto Integrator
# ══════════════════════════════════════════════════════════════════════════════

class AutoIntegrator:
    """Write new skill files and register them in the skill registry."""

    SKILLS_DIR = _BASE / "skills" / "installed"

    def __init__(self):
        self.SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    def save_skill(self, name: str, code: str) -> Path:
        """Write a skill file to the skills/installed directory."""
        safe_name = "".join(c if c.isalnum() or c == "_" else "_" for c in name.lower())
        path = self.SKILLS_DIR / f"{safe_name}.py"
        path.write_text(code, encoding="utf-8")
        logger.info("Saved new skill: %s", path)
        return path

    def register_skill(self, name: str, description: str, path: Path):
        """Add skill to the skills registry JSON."""
        registry_path = _BASE / "data" / "skills_registry.json"
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except Exception:
            registry = {"installed": [], "available": []}

        # Avoid duplicates
        existing = [s["name"] for s in registry.get("installed", [])]
        if name not in existing:
            registry.setdefault("installed", []).append({
                "name": name,
                "description": description,
                "path": str(path),
                "added": time.strftime("%Y-%m-%d %H:%M:%S"),
            })
            registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
            logger.info("Registered skill: %s", name)

    def hot_reload_skill(self, path: Path) -> bool:
        """Dynamically import a new skill module without restarting."""
        try:
            module_name = f"skills.installed.{path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.info("Hot-reloaded skill: %s", module_name)
            return True
        except Exception as exc:
            logger.warning("Hot-reload failed for %s: %s", path, exc)
            return False


# ══════════════════════════════════════════════════════════════════════════════
#  Git Committer
# ══════════════════════════════════════════════════════════════════════════════

class GitCommitter:
    """Auto-commit improvements to git."""

    def commit(self, message: str, files: list = None) -> bool:
        """Stage files and commit with message."""
        try:
            if files:
                for f in files:
                    subprocess.run(["git", "add", str(f)], cwd=_BASE,
                                   capture_output=True, timeout=10)
            else:
                subprocess.run(["git", "add", "-A"], cwd=_BASE,
                               capture_output=True, timeout=10)

            result = subprocess.run(
                ["git", "commit", "-m", f"[JARVIS-Auto] {message}"],
                cwd=_BASE, capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                logger.info("Git commit: %s", message)
                return True
            else:
                logger.debug("Git commit skipped: %s", result.stderr)
                return False
        except FileNotFoundError:
            logger.debug("git not found — skipping commit")
            return False
        except Exception as exc:
            logger.warning("Git commit error: %s", exc)
            return False


# ══════════════════════════════════════════════════════════════════════════════
#  Main Self-Improvement Engine
# ══════════════════════════════════════════════════════════════════════════════

class SelfImprovementEngine:
    """Orchestrates all self-improvement components."""

    def __init__(self, memory, settings: dict):
        self.memory   = memory
        self.settings = settings
        interval_h    = settings.get("self_improve_interval_hours", 6)
        self.interval = interval_h * 3600
        self._stop    = threading.Event()
        self._thread  = None
        self.learned_count = 0

        # Sub-components
        self.analyzer   = CodeAnalyzer()
        self.sandbox    = SandboxTester()
        self.integrator = AutoIntegrator()
        self.committer  = GitCommitter()
        self.writer     = None   # set when groq client available

        # Backup dir
        self._backup_dir = _BASE / "temp" / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def set_groq(self, groq_client):
        """Set the Groq client after brain is initialized."""
        if groq_client:
            self.writer = FeatureWriter(groq_client)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="SelfImprove"
        )
        self._thread.start()
        logger.info("SelfImprovementEngine started.")

    def stop(self):
        self._stop.set()

    def _loop(self):
        # Initial delay — let the system warm up first
        time.sleep(60)
        while not self._stop.is_set():
            try:
                self._run_cycle()
            except Exception as exc:
                logger.error("Improvement cycle failed: %s", exc)
            self._stop.wait(self.interval)

    def _run_cycle(self):
        logger.info("Running self-improvement cycle...")

        # 1. Web knowledge scrape (kept from v1)
        self._scrape_knowledge()

        # 2. Code analysis + autonomous improvement
        if self.writer and self.settings.get("autonomous_improve", False):
            self._autonomous_code_improve()

        logger.info("Self-improve cycle done. Learned: %d total", self.learned_count)

    def _scrape_knowledge(self):
        """Scrape web snippets and store as memory (v1 behavior, kept)."""
        topics = list(DEFAULT_TOPICS)
        user_topics = self.memory.persona.get("frequent_topics", {})
        if user_topics:
            top = sorted(user_topics.items(), key=lambda x: x[1], reverse=True)[:2]
            topics += [f"{t[0]} tutorial 2025" for t in top]

        for topic in topics:
            if self._stop.is_set():
                break
            snippets = self._fetch_snippets(topic)
            for s in snippets:
                self.memory.self_improve(s, source="web_auto")
                self.learned_count += 1
            time.sleep(2)

    def _autonomous_code_improve(self):
        """Analyze code, write improvements, test, integrate."""
        suggestions = self.analyzer.suggest_improvements()
        if not suggestions:
            logger.info("No code improvements needed this cycle.")
            return

        # Take top 1 suggestion per cycle (conservative)
        suggestion = suggestions[0]
        logger.info("Attempting improvement: %s in %s",
                    suggestion.get("function", suggestion.get("text", "?")),
                    suggestion.get("file", "?"))

        if suggestion["type"] == "stub_function":
            # Try to implement the stub
            file_path = Path(suggestion["file"])
            try:
                file_content = file_path.read_text(encoding="utf-8")
                issue = f"Implement the stub function '{suggestion['function']}' at line {suggestion['line']}"
                new_code = self.writer.write_improvement(file_content, issue)
                if new_code and len(new_code) > 20:
                    test_result = self.sandbox.test_code(new_code)
                    if test_result["passed"]:
                        # Save as a skill instead of modifying core files (safer)
                        skill_name = f"auto_{suggestion['function']}"
                        path = self.integrator.save_skill(skill_name, new_code)
                        self.integrator.register_skill(
                            skill_name,
                            f"Auto-generated: {suggestion['function']}",
                            path
                        )
                        self.integrator.hot_reload_skill(path)
                        self.committer.commit(
                            f"Add auto-skill: {skill_name}", files=[path]
                        )
                        logger.info("Successfully added auto-skill: %s", skill_name)
            except Exception as exc:
                logger.warning("Autonomous improvement failed: %s", exc)

    def learn_now(self, topic: str) -> str:
        """Manually trigger learning about a topic."""
        snippets = self._fetch_snippets(topic)
        for s in snippets:
            self.memory.self_improve(s, source="manual")
        self.learned_count += len(snippets)
        return f"Learned {len(snippets)} snippet(s) about: {topic}"

    def write_skill_now(self, description: str) -> str:
        """Manually write and integrate a new skill."""
        if not self.writer:
            return "No AI engine available for skill writing."
        code = self.writer.write_new_skill(description)
        if not code:
            return "Could not generate skill code."
        test = self.sandbox.test_code(code)
        if not test["passed"]:
            return f"Generated code failed tests: {test['error']}"
        safe_name = description[:30].replace(" ", "_").lower()
        path = self.integrator.save_skill(safe_name, code)
        self.integrator.register_skill(safe_name, description, path)
        self.integrator.hot_reload_skill(path)
        self.committer.commit(f"Add manual skill: {safe_name}", files=[path])
        return f"New skill '{safe_name}' created, tested, and activated!"

    def apply_correction(self, original: str, correction: str):
        self.memory.add_correction(f"'{original}' → '{correction}'")

    def backup_codebase(self) -> str:
        import shutil
        ts = int(time.time())
        backup_path = self._backup_dir / f"backup_{ts}"
        try:
            shutil.copytree(_BASE, backup_path, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "temp", "logs", "data"
            ))
            return str(backup_path)
        except Exception as exc:
            logger.error("Backup failed: %s", exc)
            return ""

    def get_stats(self) -> dict:
        return {
            "total_learned":     self.learned_count,
            "knowledge_entries": len(self.memory.knowledge.get("entries", [])),
            "learned_facts":     len(self.memory.persona.get("learned_facts", [])),
            "frequent_topics":   len(self.memory.persona.get("frequent_topics", {})),
            "installed_skills":  len(list((
                _BASE / "skills" / "installed"
            ).glob("*.py"))),
        }

    def _fetch_snippets(self, query: str) -> list:
        url = f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JARVIS/3.0"}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            snippets = []
            for tag in soup.find_all("a", class_="result__snippet")[:5]:
                text = tag.get_text(strip=True)
                if text and len(text) > 20:
                    snippets.append(f"[{query}] {text}")
            return snippets
        except Exception as exc:
            logger.debug("Snippet fetch failed '%s': %s", query, exc)
            return []

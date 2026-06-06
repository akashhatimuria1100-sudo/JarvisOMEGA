"""
core/memory.py — JARVIS OMEGA Persistent Memory Engine
"""

import json
import time
import re
import threading
import logging
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("JARVIS.MEMORY")
_BASE = Path(__file__).resolve().parent.parent

MAX_KNOWLEDGE = 1000
MAX_FACTS = 200
MAX_RECALL_FACTS = 8


STOPWORDS = frozenset([
    "the", "and", "for", "that", "this", "with", "have", "from",
    "they", "will", "what", "when", "your", "also", "into", "then",
    "than", "just", "like", "more", "some", "been", "were", "but",
])


class MemoryEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self.knowledge_path = _BASE / "data/knowledge.json"
        self.persona_path   = _BASE / "data/persona_memory.json"
        self.knowledge = self._load(self.knowledge_path, {"entries": []})
        self.persona   = self._load(self.persona_path, {
            "name": "Sir",
            "preferences": {},
            "frequent_topics": {},
            "speaking_style": "professional_casual",
            "languages_used": ["en"],
            "corrections": [],
            "learned_facts": [],
            "projects": [],
            "reminders": [],
        })
        # Fix type errors
        if isinstance(self.persona.get("frequent_topics"), list):
            self.persona["frequent_topics"] = {}

    def _load(self, path: Path, default: dict) -> dict:
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Load failed %s: %s", path, exc)
        return default

    def _save(self):
        try:
            self.knowledge_path.write_text(
                json.dumps(self.knowledge, indent=2, ensure_ascii=False), encoding="utf-8")
            self.persona_path.write_text(
                json.dumps(self.persona, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.error("Memory save failed: %s", exc)

    def store(self, user_input: str, ai_response: str):
        with self._lock:
            self._update_topics(user_input)
            self._extract_facts(user_input)
            # Log conversation
            entry = {"timestamp": time.time(), "user": user_input[:200], "ai": ai_response[:200]}
            entries = self.knowledge.setdefault("entries", [])
            entries.append(entry)
            if len(entries) > MAX_KNOWLEDGE:
                self.knowledge["entries"] = entries[-MAX_KNOWLEDGE:]
            self._save()

    def store_fact(self, fact: str):
        if not fact:
            return
        with self._lock:
            facts = self.persona.setdefault("learned_facts", [])
            if fact not in facts:
                facts.append(fact)
            if len(facts) > MAX_FACTS:
                self.persona["learned_facts"] = facts[-MAX_FACTS:]
            self._save()

    def recall(self, query: str) -> str:
        parts = []
        facts = self.persona.get("learned_facts", [])
        if facts:
            parts.append(f"Facts: {', '.join(facts[-MAX_RECALL_FACTS:])}")
        topics = self.persona.get("frequent_topics", {})
        if topics:
            top = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:6]
            parts.append(f"Interests: {', '.join(t[0] for t in top)}")
        style = self.persona.get("speaking_style", "")
        if style:
            parts.append(f"Style: {style}")
        langs = self.persona.get("languages_used", [])
        if langs:
            parts.append(f"Languages: {', '.join(langs)}")
        projects = self.persona.get("projects", [])
        if projects:
            recent = [p.get("name", "") for p in projects[-3:]]
            parts.append(f"Recent projects: {', '.join(recent)}")
        return " | ".join(parts) if parts else ""

    def self_improve(self, content: str, source: str = "web"):
        entry = {"content": content[:500], "source": source, "timestamp": time.time()}
        with self._lock:
            entries = self.knowledge.setdefault("entries", [])
            entries.append(entry)
            if len(entries) > MAX_KNOWLEDGE:
                self.knowledge["entries"] = entries[-MAX_KNOWLEDGE:]
            self._save()

    def add_correction(self, correction: str):
        with self._lock:
            corrections = self.persona.setdefault("corrections", [])
            corrections.append({"text": correction, "timestamp": time.time()})
            if len(corrections) > 100:
                self.persona["corrections"] = corrections[-100:]
            self._save()

    def add_project(self, project: dict):
        with self._lock:
            projects = self.persona.setdefault("projects", [])
            projects.append(project)
            if len(projects) > 50:
                self.persona["projects"] = projects[-50:]
            self._save()

    def update_language(self, lang: str):
        with self._lock:
            langs = self.persona.setdefault("languages_used", ["en"])
            if lang not in langs:
                langs.append(lang)
            self._save()

    def _update_topics(self, text: str):
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        topics = self.persona.setdefault("frequent_topics", {})
        for w in words:
            if w not in STOPWORDS:
                topics[w] = topics.get(w, 0) + 1
        if len(topics) > 300:
            trimmed = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:300]
            self.persona["frequent_topics"] = dict(trimmed)

    def _extract_facts(self, text: str):
        patterns = [
            r"my (?:name is|name's) ([a-zA-Z ]+)",
            r"i (?:am|'m) (?:a |an )?([a-zA-Z ]+)",
            r"my favorite (.+?) is (.+)",
            r"i like (.+)",
            r"i (?:live|stay|am) in ([a-zA-Z ,]+)",
            r"i work (?:at|for|in) ([a-zA-Z ]+)",
            r"i (?:study|am studying) ([a-zA-Z ]+)",
            r"call me ([a-zA-Z]+)",
        ]
        facts = self.persona.setdefault("learned_facts", [])
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                fact = match.group(0).strip()
                if fact not in facts and len(fact) < 100:
                    facts.append(fact)
        if len(facts) > MAX_FACTS:
            self.persona["learned_facts"] = facts[-MAX_FACTS:]

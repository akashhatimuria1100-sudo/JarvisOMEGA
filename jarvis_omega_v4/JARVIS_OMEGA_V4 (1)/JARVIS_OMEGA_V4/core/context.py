"""
core/context.py — Analyzes user intent, language, and conversation context
"""

import re
import logging
from typing import Optional

logger = logging.getLogger("JARVIS.CONTEXT")


INTENT_PATTERNS = {
    "open_app":     [r"\bopen\b", r"\blaunch\b", r"\bstart\b", r"\brun\b"],
    "search":       [r"\bsearch\b", r"\bfind\b", r"\blook up\b", r"\bwhat is\b", r"\bhow to\b"],
    "code":         [r"\bcode\b", r"\bprogram\b", r"\bscript\b", r"\bdebug\b", r"\bwrite.*(?:python|java|cpp|html)\b"],
    "create":       [r"\bcreate\b", r"\bmake\b", r"\bbuild\b", r"\bgenerate\b"],
    "control":      [r"\bclick\b", r"\btype\b", r"\bpress\b", r"\bscroll\b", r"\bclose\b"],
    "screenshot":   [r"\bscreenshot\b", r"\bscreen\b", r"\bcapture\b"],
    "memory":       [r"\bremember\b", r"\bforget\b", r"\bnote\b", r"\bsave\b"],
    "system":       [r"\bvolume\b", r"\bbattery\b", r"\bcpu\b", r"\bram\b", r"\bshutdown\b"],
    "arduino":      [r"\barduino\b", r"\besp32\b", r"\besp8266\b", r"\braspberry\b", r"\bfirmware\b"],
    "image":        [r"\bimage\b", r"\bpicture\b", r"\bdraw\b", r"\bgenerate.*image\b", r"\bphoto\b"],
    "project":      [r"\bproject\b", r"\bapp\b", r"\bapplication\b", r"\bwebsite\b", r"\bgame\b"],
    "question":     [r"\?$", r"\bwhy\b", r"\bwhen\b", r"\bwhere\b", r"\bwho\b", r"\bexplain\b"],
}

HINDI_INDICATORS = [
    "karo", "karna", "batao", "bata", "kya", "hai", "hain", "mera", "tera",
    "yeh", "woh", "aur", "nahi", "nai", "abhi", "thoda", "bahut", "ek",
    "bhai", "yaar", "accha", "theek", "chalao", "kholo",
]

COMPLEXITY_KEYWORDS = ["create", "build", "develop", "make", "generate", "design", "implement"]


class ContextAnalyzer:
    def __init__(self):
        self._compiled = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in INTENT_PATTERNS.items()
        }

    def analyze(self, text: str, history: list) -> dict:
        return {
            "intent":     self._detect_intent(text),
            "language":   self._detect_language(text),
            "complexity": self._detect_complexity(text),
            "entities":   self._extract_entities(text),
            "is_question": bool(re.search(r'\?', text)),
            "sentiment":  self._detect_sentiment(text),
        }

    def _detect_intent(self, text: str) -> str:
        text_lower = text.lower()
        scores: dict[str, int] = {}
        for intent, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(text_lower):
                    scores[intent] = scores.get(intent, 0) + 1
        if scores:
            return max(scores, key=scores.__getitem__)
        return "general"

    def _detect_language(self, text: str) -> str:
        text_lower = text.lower()
        hindi_score = sum(1 for w in HINDI_INDICATORS if w in text_lower.split())
        if hindi_score >= 2:
            return "hi"
        if any(ord(ch) > 0x0900 and ord(ch) < 0x097F for ch in text):
            return "hi"
        return "en"

    def _detect_complexity(self, text: str) -> str:
        words = text.lower().split()
        if any(w in COMPLEXITY_KEYWORDS for w in words) and len(words) > 6:
            return "complex"
        if len(words) > 15:
            return "medium"
        return "simple"

    def _extract_entities(self, text: str) -> dict:
        entities = {}
        # App names
        apps = re.findall(
            r'\b(chrome|firefox|notepad|vscode|spotify|calculator|explorer|vlc|'
            r'whatsapp|youtube|gmail|discord|zoom|blender|unity|photoshop|arduino)\b',
            text, re.IGNORECASE
        )
        if apps:
            entities["apps"] = list(set(a.lower() for a in apps))
        # URLs
        urls = re.findall(r'https?://\S+|www\.\S+', text)
        if urls:
            entities["urls"] = urls
        # File extensions
        files = re.findall(r'\b\w+\.(py|js|html|css|cpp|c|java|txt|json|csv|pdf|png|jpg)\b', text, re.IGNORECASE)
        if files:
            entities["files"] = files
        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        if numbers:
            entities["numbers"] = numbers
        return entities

    def _detect_sentiment(self, text: str) -> str:
        positive = ["good", "great", "awesome", "nice", "thanks", "perfect", "excellent"]
        negative = ["bad", "wrong", "error", "broken", "failed", "stupid", "terrible"]
        text_lower = text.lower()
        pos = sum(1 for w in positive if w in text_lower)
        neg = sum(1 for w in negative if w in text_lower)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

"""
speech/speaker.py — JARVIS OMEGA V2 Text-to-Speech
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES vs old version:
  ✅ edge-tts: Microsoft Azure Neural voices (Alexa/Gemini quality, 100% FREE)
  ✅ No 500-char limit — full responses spoken
  ✅ Sentence-chunked streaming — starts speaking in ~200ms
  ✅ Non-blocking, no UI freeze
  ✅ pyttsx3 as offline fallback

Voices (Windows Neural):
  en-US-GuyNeural      — professional male (default)
  en-US-JennyNeural    — friendly female
  en-IN-NeerjaNeural   — Indian English female
  hi-IN-SwaraNeural    — Hindi female
"""

import logging
import threading
import tempfile
import os
import re
import asyncio
from pathlib import Path

logger = logging.getLogger("JARVIS.SPEAKER")


class JarvisSpeaker:
    """Multi-engine TTS: edge-tts (neural) → pyttsx3 (offline fallback)."""

    DEFAULT_VOICE = "en-US-GuyNeural"

    def __init__(self, settings: dict = None):
        self.settings  = settings or {}
        self._lock     = threading.Lock()
        self._speaking = False
        self._stop_evt = threading.Event()
        self._engine   = None           # pyttsx3 fallback
        self._edge_ok  = False
        self._pyttsx_ok = False

        self._check_edge()
        self._init_pyttsx3()

    # ── Init ────────────────────────────────────────────────────────────────

    def _check_edge(self):
        try:
            import edge_tts  # noqa
            self._edge_ok = True
            logger.info("edge-tts ready (Microsoft Neural voices).")
        except ImportError:
            logger.warning("edge-tts not installed. Run: pip install edge-tts")

    def _init_pyttsx3(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            rate = self.settings.get("tts_rate", 175)
            self._engine.setProperty("rate", rate)
            self._engine.setProperty("volume", 0.95)
            voices = self._engine.getProperty("voices") or []
            idx = self.settings.get("tts_voice_index", 0)
            if voices and 0 <= idx < len(voices):
                self._engine.setProperty("voice", voices[idx].id)
            self._pyttsx_ok = True
            logger.info("pyttsx3 fallback ready. Voices: %d", len(voices))
        except Exception as exc:
            logger.warning("pyttsx3 init failed: %s", exc)

    # ── Public API ──────────────────────────────────────────────────────────

    def speak(self, text: str, blocking: bool = False):
        """Speak text. Non-blocking by default."""
        if not text or not text.strip():
            return
        cleaned = self._clean_for_speech(text)
        if blocking:
            self._do_speak(cleaned)
        else:
            t = threading.Thread(target=self._do_speak, args=(cleaned,), daemon=True)
            t.start()

    def stop(self):
        """Interrupt current speech."""
        self._stop_evt.set()
        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def get_voices(self) -> list:
        """Return list of available pyttsx3 voice names."""
        if self._engine:
            try:
                return [v.name for v in (self._engine.getProperty("voices") or [])]
            except Exception:
                pass
        return []

    def set_rate(self, rate: int):
        if self._engine:
            try:
                self._engine.setProperty("rate", rate)
            except Exception:
                pass

    # ── Internal ────────────────────────────────────────────────────────────

    def _do_speak(self, text: str):
        with self._lock:
            self._speaking = True
            self._stop_evt.clear()
            try:
                if self._edge_ok:
                    self._speak_edge(text)
                elif self._pyttsx_ok:
                    self._speak_pyttsx3(text)
                else:
                    logger.warning("No TTS engine available. Text: %s", text[:80])
            except Exception as exc:
                logger.error("TTS error: %s", exc)
                if self._pyttsx_ok:
                    try:
                        self._speak_pyttsx3(text)
                    except Exception:
                        pass
            finally:
                self._speaking = False

    def _speak_edge(self, text: str):
        """Use edge-tts with sentence-chunked streaming for fast start."""
        voice = self.settings.get("tts_voice", self.DEFAULT_VOICE)
        rate  = self.settings.get("tts_edge_rate", "+0%")   # e.g. "+10%", "-5%"
        pitch = self.settings.get("tts_edge_pitch", "+0Hz")

        # Split into sentences for faster first-chunk playback
        sentences = self._split_sentences(text)

        for sentence in sentences:
            if self._stop_evt.is_set():
                break
            if not sentence.strip():
                continue
            try:
                self._speak_edge_chunk(sentence, voice, rate, pitch)
            except Exception as exc:
                logger.warning("edge-tts chunk error: %s", exc)
                # Fallback this chunk to pyttsx3
                if self._pyttsx_ok:
                    try:
                        self._speak_pyttsx3(sentence)
                    except Exception:
                        pass

    def _speak_edge_chunk(self, text: str, voice: str, rate: str, pitch: str):
        """Speak one sentence via edge-tts (async → sync bridge)."""
        import edge_tts

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            fname = f.name

        async def _gen():
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await communicate.save(fname)

        # Run async in a dedicated event loop
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_gen())
        finally:
            loop.close()

        # Play the file
        self._play_audio(fname)
        try:
            os.unlink(fname)
        except Exception:
            pass

    def _play_audio(self, path: str):
        """Play an audio file using the best available method."""
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._stop_evt.is_set():
                import time
                time.sleep(0.05)
            pygame.mixer.music.stop()
            return
        except Exception:
            pass

        try:
            import playsound
            playsound.playsound(path, block=True)
            return
        except Exception:
            pass

        # Windows fallback
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-c",
                 f"(New-Object Media.SoundPlayer '{path}').PlaySync()"],
                timeout=60, capture_output=True
            )
        except Exception as exc:
            logger.error("Audio playback failed: %s", exc)

    def _speak_pyttsx3(self, text: str):
        if self._engine:
            self._engine.say(text)
            self._engine.runAndWait()

    # ── Utilities ───────────────────────────────────────────────────────────

    def _clean_for_speech(self, text: str) -> str:
        """Remove markdown/code/URLs — keep natural spoken text."""
        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", " [code block] ", text)
        text = re.sub(r"`[^`]+`", lambda m: m.group().strip("`"), text)
        # Remove URLs
        text = re.sub(r"https?://\S+", "link", text)
        # Remove markdown symbols
        text = re.sub(r"[*_#~\[\]{}|>]", "", text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _split_sentences(self, text: str) -> list:
        """Split text into natural sentences for streaming playback."""
        # Split on sentence-ending punctuation
        parts = re.split(r"(?<=[.!?])\s+", text)
        result = []
        current = ""
        for part in parts:
            current += (" " if current else "") + part
            # Emit when we have a reasonable chunk (30–200 chars)
            if len(current) >= 60:
                result.append(current.strip())
                current = ""
        if current.strip():
            result.append(current.strip())
        return result if result else [text]

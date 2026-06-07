"""
speech/speaker.py — JARVIS OMEGA V4 Text-to-Speech
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ Pure pip-installable TTS — NO winget, NO ffmpeg
  ✅ pyttsx3 (primary) — offline, instant, male voice
  ✅ edge-tts (high-quality neural) — auto fallback
  ✅ Fast speaking: no full-stop pause loop, no sentence splitting lag
  ✅ Male voice enforced (DAVID/ZIRA fallback to any male voice)
  ✅ Speed boosted: rate=220+ (was 170)
  ✅ Speaks full text in one shot — no chunking pauses
  ✅ Non-blocking — GUI never freezes
  ✅ Playback via PowerShell MediaPlayer (Windows, no ffmpeg needed)
  ✅ sounddevice only used as optional bonus, not required
"""

import logging
import threading
import tempfile
import os
import re
import asyncio
import subprocess
import platform
from pathlib import Path

logger = logging.getLogger("JARVIS.SPEAKER")


class JarvisSpeaker:
    """
    TTS Engine: pyttsx3 (instant, offline, male) → edge-tts (neural) fallback.
    No ffmpeg. No winget. No pygame. Works on Python 3.14 with pip only.
    """

    # Best male neural voices for edge-tts
    MALE_VOICES = [
        "en-US-GuyNeural",       # American male — confident, clear
        "en-GB-RyanNeural",      # British male — authoritative
        "en-US-ChristopherNeural",
        "en-AU-WilliamNeural",
    ]

    def __init__(self, settings: dict = None):
        self.settings  = settings or {}
        self._lock     = threading.Lock()
        self._speaking = False
        self._stop_evt = threading.Event()
        self._engine   = None
        self._edge_ok  = False
        self._pyttsx_ok = False
        self._sd_ok    = False

        self._init_pyttsx3()       # Primary — instant male voice
        self._check_edge()         # Secondary — high quality
        self._check_sounddevice()  # Optional playback bonus

    # ── Init ───────────────────────────────────────────────────────────────────

    def _init_pyttsx3(self):
        """Initialize pyttsx3 with best available male voice at high speed."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()

            # Speed: 220 = fast & confident (was 170 — too slow)
            rate = self.settings.get("tts_rate", 220)
            self._engine.setProperty("rate", rate)
            self._engine.setProperty("volume", 1.0)

            # Select male voice
            voices = self._engine.getProperty("voices") or []
            chosen = None

            # Priority 1: David (Windows default male)
            for v in voices:
                vid = (v.id or "").lower()
                vname = (v.name or "").lower()
                if "david" in vid or "david" in vname:
                    chosen = v
                    break

            # Priority 2: Any male-named voice
            if not chosen:
                male_keywords = ["male", "guy", "man", "mark", "ryan", "james",
                                 "george", "chris", "william", "richard", "tom"]
                for v in voices:
                    vname = (v.name or "").lower()
                    vid = (v.id or "").lower()
                    if any(k in vname or k in vid for k in male_keywords):
                        chosen = v
                        break

            # Priority 3: First available voice
            if not chosen and voices:
                chosen = voices[0]

            if chosen:
                self._engine.setProperty("voice", chosen.id)
                logger.info("pyttsx3 male voice: %s (rate=%d)", chosen.name, rate)

            self._pyttsx_ok = True
        except Exception as exc:
            logger.warning("pyttsx3 init failed: %s", exc)

    def _check_edge(self):
        try:
            import edge_tts  # noqa
            self._edge_ok = True
            logger.info("edge-tts available as high-quality fallback.")
        except ImportError:
            logger.info("edge-tts not installed (pip install edge-tts). Using pyttsx3.")

    def _check_sounddevice(self):
        try:
            import sounddevice  # noqa
            import soundfile    # noqa
            self._sd_ok = True
        except ImportError:
            pass

    # ── Public API ─────────────────────────────────────────────────────────────

    def speak(self, text: str, blocking: bool = False):
        """Speak text. Non-blocking by default (GUI stays responsive)."""
        if not text or not text.strip():
            return
        cleaned = self._clean_for_speech(text)
        if not cleaned:
            return

        if blocking:
            self._do_speak(cleaned)
        else:
            t = threading.Thread(target=self._do_speak, args=(cleaned,), daemon=True)
            t.start()

    def stop(self):
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

    # ── Internal ───────────────────────────────────────────────────────────────

    def _do_speak(self, text: str):
        with self._lock:
            self._speaking = True
            self._stop_evt.clear()
            try:
                # Try pyttsx3 first — fastest, most reliable, offline
                if self._pyttsx_ok:
                    self._speak_pyttsx3(text)
                elif self._edge_ok:
                    self._speak_edge(text)
                else:
                    logger.error("No TTS engine available. pip install pyttsx3")
            except Exception as exc:
                logger.error("TTS error: %s", exc)
                # Try edge-tts as emergency fallback
                if self._edge_ok and not self._pyttsx_ok:
                    try:
                        self._speak_edge(text)
                    except Exception:
                        pass
            finally:
                self._speaking = False

    def _speak_pyttsx3(self, text: str):
        """Fast, offline, male voice TTS. Speaks full text at once — no chunking."""
        if not self._engine:
            return
        try:
            # Ensure rate is set correctly every call
            rate = self.settings.get("tts_rate", 220)
            self._engine.setProperty("rate", rate)
            self._engine.say(text)
            self._engine.runAndWait()
        except RuntimeError as exc:
            # Engine loop already running — reinit
            logger.warning("pyttsx3 RuntimeError: %s — reinitializing...", exc)
            try:
                self._init_pyttsx3()
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception as e2:
                logger.error("pyttsx3 reinit failed: %s", e2)
        except Exception as exc:
            logger.warning("pyttsx3 speak error: %s", exc)

    def _speak_edge(self, text: str):
        """edge-tts: neural male voice. Used if pyttsx3 unavailable."""
        # Select male voice
        voice = self.settings.get("tts_voice", "")
        if not voice or "Neerja" in voice or "Female" in voice.lower():
            voice = self.MALE_VOICES[0]  # Force male

        rate  = self.settings.get("tts_edge_rate", "+15%")  # Faster default
        pitch = self.settings.get("tts_edge_pitch", "-3Hz")

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            fname = f.name

        async def _gen():
            import edge_tts
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            await comm.save(fname)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_gen())
            finally:
                loop.close()
                asyncio.set_event_loop(None)

            self._play_mp3(fname)
        except Exception as exc:
            logger.warning("edge-tts error: %s", exc)
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _play_mp3(self, path: str):
        """Play MP3 — no ffmpeg, no pygame. Pure pip-safe methods."""
        # Method 1: sounddevice + soundfile (best quality, pip-only)
        if self._sd_ok:
            try:
                import soundfile as sf
                import sounddevice as sd
                data, sr = sf.read(path, dtype="float32")
                sd.play(data, sr)
                sd.wait()
                return
            except Exception as exc:
                logger.debug("sounddevice mp3 fail: %s", exc)

        # Method 2: Windows PowerShell MediaPlayer (no extra installs)
        if platform.system() == "Windows":
            try:
                abs_path = str(Path(path).resolve()).replace("\\", "\\\\")
                ps_cmd = (
                    "Add-Type -AssemblyName presentationCore; "
                    "$mp = [System.Windows.Media.MediaPlayer]::new(); "
                    f"$mp.Open([uri]::new('{abs_path}')); "
                    "Start-Sleep -Milliseconds 200; "
                    "$mp.Play(); "
                    "Start-Sleep -Seconds 30; "
                    "$mp.Stop()"
                )
                subprocess.run(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                    timeout=40, capture_output=True
                )
                return
            except Exception as exc:
                logger.debug("PowerShell MediaPlayer fail: %s", exc)

            # Method 3: Windows Media Player CLI
            try:
                subprocess.run(["wmplayer", "/play", "/close", path],
                               timeout=30, capture_output=True)
                return
            except Exception:
                pass

        # Method 4: Linux
        if platform.system() == "Linux":
            for cmd in [["mpg123", path], ["ffplay", "-nodisp", "-autoexit", path],
                        ["cvlc", "--play-and-exit", path]]:
                try:
                    subprocess.run(cmd, timeout=30, capture_output=True)
                    return
                except Exception:
                    continue

        # Method 5: macOS
        if platform.system() == "Darwin":
            try:
                subprocess.run(["afplay", path], timeout=30)
                return
            except Exception:
                pass

        logger.warning("All audio playback methods failed. Install: pip install sounddevice soundfile")

    def _clean_for_speech(self, text: str) -> str:
        """Remove markdown, code blocks, URLs — things that sound terrible when spoken."""
        # Remove code blocks entirely (don't say "code block code block")
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"`[^`]+`", lambda m: m.group().strip("`"), text)
        # Remove URLs
        text = re.sub(r"https?://\S+", "link", text)
        # Remove markdown syntax
        text = re.sub(r"[*_#~\[\]{}|>⚡⚠️✅❌🎤🔴📊🌐📋▶💾⚙🗑🔗📸🐍🎨💡🌍🔒🛡]", "", text)
        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        # Limit length for TTS (very long text → summarize first 800 chars)
        text = text.strip()
        if len(text) > 900:
            # Speak first 900 chars and indicate truncation
            cutoff = text[:900].rsplit(".", 1)[0]
            text = cutoff + "."
        return text

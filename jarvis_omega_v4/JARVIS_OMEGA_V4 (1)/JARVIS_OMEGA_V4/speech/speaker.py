"""
speech/speaker.py — JARVIS OMEGA V4 Text-to-Speech
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ Dedicated TTS worker thread + queue — eliminates lock deadlocks
  ✅ pyttsx3 runs in isolated subprocess — no "speaks once" hang
  ✅ Robust fallback: pyttsx3 → edge-tts → error log
  ✅ Male voice enforced (David/Guy) at rate 220
  ✅ Non-blocking by default; optional blocking with timeout
  ✅ Playback via sounddevice / PowerShell / native OS players
  ✅ Strips markdown, URLs, emoji before speaking
"""

import sys
import logging
import threading
import tempfile
import os
import re
import asyncio
import subprocess
import platform
import queue
import base64
from pathlib import Path

logger = logging.getLogger("JARVIS.SPEAKER")


class JarvisSpeaker:
    """
    TTS Engine: pyttsx3 (offline, male) via subprocess → edge-tts (neural) fallback.
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
        self.settings   = settings or {}
        self._speaking  = False
        self._stop_evt  = threading.Event()
        self._pyttsx_ok = False
        self._edge_ok   = False
        self._sd_ok     = False

        self._tts_queue  = queue.Queue()
        self._tts_thread = threading.Thread(target=self._tts_loop, daemon=True)
        self._tts_thread.start()

        self._check_pyttsx3()
        self._check_edge()
        self._check_sounddevice()

    # ── Init checks ───────────────────────────────────────────────────────────

    def _check_pyttsx3(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.stop()
            del engine
            self._pyttsx_ok = True
            logger.info("pyttsx3 available (subprocess mode).")
        except Exception as exc:
            logger.warning("pyttsx3 not available: %s", exc)

    def _check_edge(self):
        try:
            import edge_tts  # noqa
            self._edge_ok = True
            logger.info("edge-tts available as high-quality fallback.")
        except ImportError:
            logger.info("edge-tts not installed (pip install edge-tts).")

    def _check_sounddevice(self):
        try:
            import sounddevice  # noqa
            import soundfile    # noqa
            self._sd_ok = True
        except ImportError:
            pass

    # ── Worker thread ─────────────────────────────────────────────────────────

    def _tts_loop(self):
        """Single consumer thread — processes one utterance at a time."""
        while True:
            item = self._tts_queue.get()
            if item is None:
                break
            text, event = item
            try:
                self._do_speak(text)
            except Exception as exc:
                logger.error("TTS worker error: %s", exc)
            finally:
                self._speaking = False
                if event is not None:
                    event.set()

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str, blocking: bool = False):
        """Queue text for speaking. Non-blocking by default."""
        if not text or not text.strip():
            return
        cleaned = self._clean_for_speech(text)
        if not cleaned:
            return

        self._speaking = True
        event = threading.Event() if blocking else None
        self._tts_queue.put((cleaned, event))
        if blocking and event is not None:
            event.wait(timeout=60)

    def stop(self):
        self._stop_evt.set()
        self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking or not self._tts_queue.empty()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _do_speak(self, text: str):
        self._speaking = True
        self._stop_evt.clear()
        # Try pyttsx3 first (offline, instant, male)
        if self._pyttsx_ok:
            try:
                self._speak_pyttsx3_subprocess(text)
                return
            except Exception as exc:
                logger.warning("pyttsx3 subprocess failed (%s), trying edge-tts...", exc)
        # Fallback to edge-tts (neural, requires internet)
        if self._edge_ok:
            try:
                self._speak_edge(text)
                return
            except Exception as exc:
                logger.warning("edge-tts fallback failed: %s", exc)
        logger.error("No TTS engine available. Install: pip install pyttsx3 edge-tts")

    def _speak_pyttsx3_subprocess(self, text: str):
        """
        Run pyttsx3 in a fresh subprocess — completely sidesteps the
        well-known 'runAndWait() hangs after first call' bug.
        """
        import pyttsx3  # check we can import it here too
        # Encode text so we don't fight shell escaping
        text_b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
        rate = self.settings.get("tts_rate", 220)

        script = f'''
import base64, pyttsx3
TEXT = base64.b64decode("{text_b64}").decode("utf-8")
engine = pyttsx3.init()
engine.setProperty("rate", {rate})
engine.setProperty("volume", 1.0)
voices = engine.getProperty("voices")
chosen = None
for v in voices:
    vid = (v.id or "").lower()
    vname = (v.name or "").lower()
    if "david" in vid or "david" in vname:
        chosen = v
        break
if not chosen:
    keywords = ["male", "guy", "man", "mark", "ryan", "james",
                "george", "chris", "william", "richard", "tom"]
    for v in voices:
        if any(k in (v.name or "").lower() for k in keywords):
            chosen = v
            break
if chosen:
    engine.setProperty("voice", chosen.id)
engine.say(TEXT)
engine.runAndWait()
engine.stop()
'''
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(script)
            script_path = f.name

        kwargs = {}
        if platform.system() == "Windows" and hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                [Path(sys.executable).as_posix(), script_path],
                timeout=30, capture_output=True, text=True, **kwargs
            )
            if result.returncode != 0:
                err = result.stderr.strip() or "unknown subprocess error"
                raise RuntimeError(f"pyttsx3 subprocess error: {err}")
        finally:
            try:
                os.unlink(script_path)
            except Exception:
                pass

    def _speak_edge(self, text: str):
        """edge-tts: neural male voice."""
        voice = self.settings.get("tts_voice", "")
        if not voice or "Neerja" in voice or "Female" in voice.lower():
            voice = self.MALE_VOICES[0]  # Force male

        rate  = self.settings.get("tts_edge_rate", "+15%")
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
                kwargs = {}
                if hasattr(subprocess, "CREATE_NO_WINDOW"):
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                subprocess.run(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                    timeout=40, capture_output=True, **kwargs
                )
                return
            except Exception as exc:
                logger.debug("PowerShell MediaPlayer fail: %s", exc)

            # Method 3: Windows Media Player CLI
            try:
                kwargs = {}
                if hasattr(subprocess, "CREATE_NO_WINDOW"):
                    kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
                subprocess.run(["wmplayer", "/play", "/close", path],
                               timeout=30, capture_output=True, **kwargs)
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
        text = re.sub(r"```[\s\S]*?```", " ", text)
        text = re.sub(r"`[^`]+`", lambda m: m.group().strip("`"), text)
        text = re.sub(r"https?://\S+", "link", text)
        text = re.sub(r"[*_#~\[\]{}|>⚡⚠️✅❌🎤🔴📊🌐📋▶💾⚙🗑🔗📸🐍🎨💡🌍🔒🛡]", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = text.strip()
        if len(text) > 900:
            cutoff = text[:900].rsplit(".", 1)[0]
            text = cutoff + "."
        return text

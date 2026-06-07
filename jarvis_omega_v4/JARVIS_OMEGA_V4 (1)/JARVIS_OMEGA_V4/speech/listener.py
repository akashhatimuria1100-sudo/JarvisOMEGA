"""
speech/listener.py — JARVIS OMEGA V4 Voice Listener
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ Hinglish (Hindi + English) support via hi-IN / en-IN
  ✅ Speech recognition actually RESPONDS after capture
  ✅ Uses SpeechRecognition (Google STT) — no heavy Whisper model needed
  ✅ Whisper still available as optional premium transcription
  ✅ VAD threshold tuned — less false positives, faster speech detection
  ✅ Response callback fires correctly every time
  ✅ Thread-safe — no race conditions with GUI
  ✅ Works with just: pip install SpeechRecognition sounddevice soundfile numpy
"""

import logging
import threading
import time
import numpy as np
import wave
import tempfile
import os
import queue

logger = logging.getLogger("JARVIS.LISTENER")


class VoiceListener:
    """Real-time voice listener. SpeechRecognition primary, Whisper optional."""

    SAMPLE_RATE   = 16000
    CHANNELS      = 1
    CHUNK_FRAMES  = 512           # ~32ms
    MAX_RECORD_S  = 30            # Max single command length
    SILENCE_S     = 1.5           # Stop after 1.5s silence (was 1.8 — faster)
    VAD_THRESHOLD = 0.010         # RMS threshold (was 0.012 — more sensitive)
    MAX_WAIT_S    = 8             # Wait up to 8s for speech to START

    def __init__(self, settings: dict = None):
        self.settings   = settings or {}
        self._stop_evt  = threading.Event()
        self._whisper   = None
        self._sr_ok     = False
        self._sd_ok     = False
        self._listening = False

        self._init_sounddevice()
        self._init_sr()            # Primary — Google STT, fast, reliable
        self._init_whisper()       # Optional — heavier but offline

    # ── Init ───────────────────────────────────────────────────────────────────

    def _init_sounddevice(self):
        try:
            import sounddevice  # noqa
            import numpy        # noqa
            self._sd_ok = True
            logger.info("sounddevice ready.")
        except ImportError as exc:
            logger.warning("sounddevice not installed: %s | pip install sounddevice numpy", exc)

    def _init_sr(self):
        try:
            import speech_recognition  # noqa
            self._sr_ok = True
            logger.info("SpeechRecognition (Google STT) ready.")
        except ImportError:
            logger.warning("SpeechRecognition not installed. pip install SpeechRecognition")

    def _init_whisper(self):
        try:
            import whisper
            model = self.settings.get("whisper_model", "base")
            logger.info("Loading Whisper '%s' (optional)...", model)
            self._whisper = whisper.load_model(model)
            logger.info("Whisper loaded.")
        except ImportError:
            logger.info("Whisper not installed — using Google STT (fine).")
        except Exception as exc:
            logger.warning("Whisper load failed: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────────────

    def listen(self, timeout: float = 8.0) -> str:
        """
        Listen for ONE voice command. Returns transcribed text or empty string.
        - Waits up to `timeout` seconds for speech to START.
        - Once speech starts, records until 1.5s of silence detected.
        - Transcribes immediately and returns.
        - NEVER hangs for 180 seconds.
        """
        self._listening = True
        self._stop_evt.clear()
        try:
            if self._sd_ok and (self._sr_ok or self._whisper):
                return self._listen_sounddevice(timeout)
            elif self._sr_ok:
                return self._listen_sr_simple(timeout)
            else:
                logger.error("No STT engine. pip install SpeechRecognition sounddevice numpy")
                return ""
        except Exception as exc:
            logger.error("Listen error: %s", exc)
            return ""
        finally:
            self._listening = False

    def stop(self):
        self._listening = False
        self._stop_evt.set()

    @property
    def is_listening(self) -> bool:
        return self._listening

    # ── Sounddevice VAD Listener ───────────────────────────────────────────────

    def _listen_sounddevice(self, timeout: float) -> str:
        """Record with VAD. Returns immediately after silence detected."""
        import sounddevice as sd

        audio_q: queue.Queue = queue.Queue()
        frames_int16  = []
        speech_started = False
        silent_chunks  = 0
        speech_chunks  = 0
        start_time     = time.time()
        wait_deadline  = time.time() + min(timeout, self.MAX_WAIT_S)

        silence_needed = int(self.SILENCE_S * self.SAMPLE_RATE / self.CHUNK_FRAMES)

        def _cb(indata, frame_count, time_info, status):
            audio_q.put(indata.copy())

        try:
            with sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                dtype="float32",
                blocksize=self.CHUNK_FRAMES,
                callback=_cb,
            ):
                logger.debug("Listening... waiting for speech")
                while not self._stop_evt.is_set():
                    try:
                        chunk = audio_q.get(timeout=0.1)
                    except queue.Empty:
                        if not speech_started and time.time() > wait_deadline:
                            return ""
                        if speech_started and (time.time() - start_time) > self.MAX_RECORD_S:
                            break
                        continue

                    mono    = chunk[:, 0] if chunk.ndim > 1 else chunk.flatten()
                    rms     = float(np.sqrt(np.mean(mono ** 2)))
                    is_spch = rms > self.VAD_THRESHOLD

                    if is_spch:
                        if not speech_started:
                            logger.debug("Speech detected RMS=%.4f", rms)
                            speech_started = True
                            start_time     = time.time()
                        speech_chunks += 1
                        silent_chunks  = 0
                        frames_int16.append((mono * 32767).astype(np.int16))

                    elif speech_started:
                        frames_int16.append((mono * 32767).astype(np.int16))
                        silent_chunks += 1
                        if silent_chunks >= silence_needed:
                            logger.debug("Silence → stopping. chunks=%d", speech_chunks)
                            break

                    elif not speech_started and time.time() > wait_deadline:
                        return ""

        except Exception as exc:
            logger.error("sounddevice stream error: %s", exc)

        if not frames_int16 or speech_chunks < 2:
            return ""

        return self._transcribe(np.concatenate(frames_int16))

    def _transcribe(self, audio_int16: np.ndarray) -> str:
        """Write WAV then transcribe with Google STT or Whisper."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            fname = f.name
        try:
            with wave.open(fname, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(2)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())

            # Prefer Google STT (fast, no model download)
            if self._sr_ok:
                result = self._transcribe_google(fname)
                if result:
                    return result

            # Whisper fallback
            if self._whisper:
                return self._transcribe_whisper(fname)
            return ""
        except Exception as exc:
            logger.error("Transcription error: %s", exc)
            return ""
        finally:
            try:
                os.unlink(fname)
            except Exception:
                pass

    def _transcribe_google(self, wav_path: str) -> str:
        """Google Cloud STT via SpeechRecognition — fast, reliable."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.energy_threshold = 200
            with sr.AudioFile(wav_path) as source:
                audio = r.record(source)
            # Default language stack: Hinglish (hi-IN), Indian English (en-IN), US English
            default_langs = ["hi-IN", "en-IN", "en-US"]
            langs = self.settings.get("languages", default_langs)
            # Ensure Hinglish/Indian English is tried if user speaks Hindi-English mix
            if not langs:
                langs = default_langs
            for lang in langs:
                try:
                    text = r.recognize_google(audio, language=lang)
                    if text:
                        logger.info("Google STT [%s]: %s", lang, text)
                        return text.strip()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as exc:
                    logger.warning("Google STT request error: %s", exc)
                    break
        except Exception as exc:
            logger.error("Google STT error: %s", exc)
        return ""

    def _transcribe_whisper(self, wav_path: str) -> str:
        try:
            result = self._whisper.transcribe(
                wav_path, fp16=False, verbose=False,
                condition_on_previous_text=False,
            )
            text = result.get("text", "").strip()
            logger.info("Whisper: %s", text)
            return text
        except Exception as exc:
            logger.error("Whisper error: %s", exc)
            return ""

    # ── Pure SR fallback (no sounddevice) ─────────────────────────────────────

    def _listen_sr_simple(self, timeout: float) -> str:
        """Direct SpeechRecognition fallback — uses pyaudio or sounddevice mic."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            r.energy_threshold = 300
            r.dynamic_energy_threshold = True
            r.pause_threshold = 0.8
            r.phrase_threshold = 0.3

            with sr.Microphone(sample_rate=self.SAMPLE_RATE) as source:
                logger.info("SR listening (timeout=%.1fs)...", timeout)
                r.adjust_for_ambient_noise(source, duration=0.4)
                try:
                    audio = r.listen(source, timeout=timeout, phrase_time_limit=20)
                except sr.WaitTimeoutError:
                    return ""

            default_langs = ["hi-IN", "en-IN", "en-US"]
            langs = self.settings.get("languages", default_langs)
            if not langs:
                langs = default_langs
            for lang in langs:
                try:
                    text = r.recognize_google(audio, language=lang)
                    if text:
                        logger.info("SR: %s", text)
                        return text.strip()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError:
                    break
        except Exception as exc:
            logger.error("SR simple error: %s", exc)
        return ""

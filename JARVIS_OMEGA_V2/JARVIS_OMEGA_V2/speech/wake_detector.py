"""
speech/wake_detector.py — JARVIS OMEGA V2 Wake Word Detector (FINAL FIXED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIXES:
  ✅ "jarvis listen" triggers extended listening
  ✅ Better partial matching
  ✅ listen_callback parameter added
"""

import logging
import threading
import time

logger = logging.getLogger("JARVIS.WAKE")


class WakeWordDetector:
    """Wake word detector using the improved VoiceListener."""

    def __init__(self, wake_word: str = "jarvis", callback=None, 
                 listen_callback=None, settings: dict = None):
        self.wake_word = wake_word.lower()
        self.callback = callback
        self.listen_callback = listen_callback
        self.settings = settings or {}
        self._stop = threading.Event()
        self._thread = None
        self._hotkey_thread = None

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="WakeWord"
        )
        self._thread.start()
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_loop, daemon=True, name="HotkeyDetect"
        )
        self._hotkey_thread.start()
        logger.info("Wake word detector started. Word: '%s'", self.wake_word)

    def stop(self):
        self._stop.set()

    def _listen_loop(self):
        from speech.listener import VoiceListener
        listener = VoiceListener(self.settings)
        while not self._stop.is_set():
            try:
                text = listener.listen(timeout=4.0)
                if text:
                    lower = text.lower().strip()

                    # "jarvis listen" → extended listening
                    if self.wake_word in lower and "listen" in lower:
                        logger.info("Wake word + listen detected: '%s'", text)
                        if self.listen_callback:
                            self.listen_callback()
                        time.sleep(2.5)
                    # Regular wake word
                    elif self.wake_word in lower or f"hey {self.wake_word}" in lower:
                        logger.info("Wake word detected: '%s'", text)
                        if self.callback:
                            self.callback()
                        time.sleep(2.5)

            except Exception as exc:
                logger.debug("Wake loop error: %s", exc)
                time.sleep(1)

    def _hotkey_loop(self):
        try:
            import keyboard
            last_ctrl = 0.0
            ctrl_count = 0

            def on_ctrl(event):
                nonlocal last_ctrl, ctrl_count
                now = time.time()
                if now - last_ctrl < 0.5:
                    ctrl_count += 1
                    if ctrl_count >= 2:
                        ctrl_count = 0
                        logger.info("Double-Ctrl activated.")
                        if self.callback:
                            self.callback()
                else:
                    ctrl_count = 1
                last_ctrl = now

            keyboard.on_press_key("ctrl", on_ctrl)
            while not self._stop.is_set():
                time.sleep(0.5)
            keyboard.unhook_all()
        except ImportError:
            logger.debug("keyboard library not available.")
        except Exception as exc:
            logger.debug("Hotkey loop error: %s", exc)
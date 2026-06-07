"""
speech/wake_detector.py — JARVIS OMEGA V3 Wake Word Detector
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Listens continuously in background for wake word using Whisper.
"""

import logging
import threading
import time

logger = logging.getLogger("JARVIS.WAKE")


class WakeWordDetector:
    def __init__(self, wake_word: str, callback, listen_callback, settings: dict = None):
        self.wake_word       = wake_word.lower().strip()
        self.callback        = callback         # called when wake word heard
        self.listen_callback = listen_callback  # called when "jarvis listen" heard
        self.settings        = settings or {}
        self._running        = False
        self._thread         = None

    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Wake detector started (word='%s')", self.wake_word)

    def stop(self):
        self._running = False

    def _run(self):
        from speech.listener import VoiceListener
        listener = VoiceListener(self.settings)

        while self._running:
            try:
                text = listener.listen(timeout=5.0)
                if not text:
                    time.sleep(0.1)
                    continue
                text_lower = text.lower().strip()
                logger.debug("Wake detector heard: %s", text_lower)

                if f"{self.wake_word} listen" in text_lower or \
                   "jarvis listen" in text_lower or \
                   "jarvis, listen" in text_lower:
                    logger.info("'listen' trigger detected!")
                    self.listen_callback()

                elif self.wake_word in text_lower:
                    logger.info("Wake word detected!")
                    self.callback()

            except Exception as exc:
                logger.warning("Wake detector error: %s", exc)
                time.sleep(1.0)

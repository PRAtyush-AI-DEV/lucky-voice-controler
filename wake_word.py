"""
wake_word.py — "Lucky" Wake Word Detection V3
==============================================
APPROACH: Uses Vosk (already installed) to continuously listen and detect
the keyword "lucky" in real-time audio stream.

WHY THIS APPROACH:
- No custom model training required
- Vosk English model already in models/ folder
- "Lucky" is a clear English word → very good accuracy
- Works 100% offline
- No dependency on openWakeWord model availability

HOW IT WORKS:
1. Continuously streams mic audio into Vosk
2. Checks partial + final transcripts for "lucky"
3. When "lucky" found → plays beep → fires callback
4. Resets and waits for next trigger
"""

import os
import time
import json
import logging
import threading
import pyaudio

from audio_utils import rms as _rms

logger = logging.getLogger("Lucky.WakeWord")

# Audio config
FORMAT    = pyaudio.paInt16
CHANNELS  = 1
RATE      = 16000
CHUNK     = 4000

# Asset paths
ASSET_BEEP_ON  = os.path.join("assets", "beep_on.wav")
ASSET_BEEP_OFF = os.path.join("assets", "beep_off.wav")

# How long to ignore after a trigger (debounce)
COOLDOWN_SECONDS = 2.5


class WakeWordDetector:
    def __init__(self, config: dict, callback):
        self.config        = config
        self.callback      = callback
        self.beep_enabled  = config.get("beep_sound", True)

        # Wake word to listen for (customizable via config)
        self.wake_word     = config.get("wake_word", "lucky").lower()

        self.running = False
        self.thread  = None
        self._last_trigger_time = 0  # for debounce

        # Load Vosk English model (better for "Lucky" than Hindi)
        model_path_en = config.get("vosk_model_path_en", "models/vosk-model-small-en-us-0.15")
        model_path_hi = config.get("vosk_model_path_hi", "models/vosk-model-hi-0.22")

        self._vosk_model = None
        self._load_vosk(model_path_en, model_path_hi)

    # ──────────────────────────────────────────
    # Model loading
    # ──────────────────────────────────────────

    def _load_vosk(self, path_en: str, path_hi: str):
        """Load Vosk model — prefer English for wake word detection."""
        from vosk import Model

        for path, label in [(path_en, "English"), (path_hi, "Hindi")]:
            if os.path.exists(path):
                try:
                    logger.info(f"Loading Vosk {label} model for wake word detection: {path}")
                    self._vosk_model = Model(path)
                    logger.info(f"✅ Wake word detector using {label} Vosk model.")
                    print(f"\n[Lucky] Wake word model: {label} ({path})")
                    return
                except Exception as e:
                    logger.error(f"Failed to load {label} model: {e}")

        logger.error(
            "❌ No Vosk model found! Wake word detection disabled.\n"
            "   Please download models to the models/ folder:\n"
            "   → models/vosk-model-small-en-us-0.15\n"
            "   → models/vosk-model-hi-0.22"
        )

    # ──────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────

    def start(self):
        if not self._vosk_model:
            logger.error("Cannot start wake word detector — no Vosk model loaded.")
            return

        self.running = True
        self.thread  = threading.Thread(
            target=self._listen_loop, daemon=True, name="WakeWordLoop"
        )
        self.thread.start()
        logger.info(f"WakeWordDetector started — listening for: '{self.wake_word}'")
        print(f"[Lucky] 🎙️  Ready! Bol do: \"{self.wake_word.upper()}\"  ←───────────────\n")

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        logger.info("WakeWordDetector stopped.")

    # ──────────────────────────────────────────
    # Beep
    # ──────────────────────────────────────────

    def _play_beep(self):
        if not self.beep_enabled:
            return
        if os.path.exists(ASSET_BEEP_ON):
            try:
                import winsound
                winsound.PlaySound(ASSET_BEEP_ON, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception:
                pass
        try:
            import winsound
            winsound.Beep(1000, 200)
        except Exception:
            pass

    # ──────────────────────────────────────────
    # Wake word check
    # ──────────────────────────────────────────

    def _contains_wake_word(self, text: str) -> bool:
        """Return True if the transcript contains the wake word."""
        if not text:
            return False
        # Simple word-boundary check (handles "lucky", "aye lucky", "hello lucky bhai" etc.)
        words = text.lower().split()
        return self.wake_word in words

    # ──────────────────────────────────────────
    # Main listen loop
    # ──────────────────────────────────────────

    def _listen_loop(self):
        from vosk import KaldiRecognizer

        GRAMMAR = json.dumps([self.wake_word, "lucky bhai", "[unk]"])
        retry_delay = 1  # seconds, grows with backoff
        MAX_RETRY_DELAY = 30

        while self.running:
            pa = None
            stream = None
            try:
                pa     = pyaudio.PyAudio()
                stream = pa.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK
                )

                try:
                    rec = KaldiRecognizer(self._vosk_model, RATE, GRAMMAR)
                except Exception:
                    rec = KaldiRecognizer(self._vosk_model, RATE)

                logger.info("Wake word listen loop started.")
                retry_delay = 1  # reset backoff on successful start

                while self.running:
                    data = stream.read(CHUNK, exception_on_overflow=False)

                    triggered = False

                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text   = result.get("text", "")
                        if self._contains_wake_word(text):
                            triggered = True
                            logger.debug(f"Wake word in final result: '{text}'")
                    else:
                        partial = json.loads(rec.PartialResult())
                        text    = partial.get("partial", "")
                        if self._contains_wake_word(text):
                            triggered = True
                            logger.debug(f"Wake word in partial: '{text}'")

                    if triggered:
                        now = time.time()
                        if now - self._last_trigger_time < COOLDOWN_SECONDS:
                            continue

                        self._last_trigger_time = now
                        print(f"\n[LUCKY] 🎯 Wake word \"{self.wake_word}\" detected!")
                        logger.info(f"Wake word '{self.wake_word}' detected.")

                        self._play_beep()

                        try:
                            rec = KaldiRecognizer(self._vosk_model, RATE, GRAMMAR)
                        except Exception:
                            rec = KaldiRecognizer(self._vosk_model, RATE)

                        try:
                            self.callback()
                        except Exception as e:
                            logger.error(f"Error in wake word callback: {e}")

            except Exception as e:
                logger.error(f"Wake word loop error (will retry in {retry_delay}s): {e}")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            finally:
                try:
                    if stream:
                        stream.stop_stream()
                        stream.close()
                    if pa:
                        pa.terminate()
                except Exception:
                    pass

        logger.info("Wake word audio stream closed.")

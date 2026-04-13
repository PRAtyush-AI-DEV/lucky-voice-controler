"""
speech_to_text.py — Audio → Text Conversion V2
===============================================
Fixes:
- [#5] Vosk Model loaded ONCE at init — not on every command call.
       PyAudio stream opened fresh per listen (required by Vosk KaldiRecognizer
       which must be re-created each time), but model load cost is eliminated.
"""

import os
import json
import logging
import pyaudio

from audio_utils import rms as _rms

logger = logging.getLogger("Lucky.STT")

SAMPLE_RATE = 16000
CHUNK_SIZE  = 4000
CHANNELS    = 1
FORMAT      = pyaudio.paInt16
DEFAULT_SILENCE_TIMEOUT   = 0.9    # seconds of silence before stopping (lower = snappier)
DEFAULT_SILENCE_THRESHOLD = 260.0  # RMS energy threshold (lower = more sensitive)

class SpeechRecognizer:
    def __init__(self, config: dict):
        self.config   = config
        self.language = config.get("language", "hi")

        self.model_path_hi = config.get("vosk_model_path_hi", "models/vosk-model-hi-0.22")
        self.model_path_en = config.get("vosk_model_path_en", "models/vosk-model-small-en-us-0.15")

        self.active_model_path = (
            self.model_path_hi if self.language == "hi" else self.model_path_en
        )

        # FIX #5 — model loaded ONCE here at init, NOT inside listen_and_transcribe
        self._vosk_model = None
        self._load_model()

    # ──────────────────────────────────────────
    # Internal
    # ──────────────────────────────────────────

    def _load_model(self):
        try:
            from vosk import Model
            if not os.path.exists(self.active_model_path):
                logger.error(
                    f"Vosk model not found at '{self.active_model_path}'. "
                    "Please download and extract it to the models/ folder."
                )
                return

            logger.info(f"Loading Vosk model from '{self.active_model_path}' ...")
            self._vosk_model = Model(self.active_model_path)
            logger.info("Vosk STT model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Vosk: {e}")

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def listen_and_transcribe(self, idle_timeout_seconds: float = None) -> dict:
        """
        Open mic, record until silence, return transcribed text.
        KaldiRecognizer is lightweight and created fresh each call (required).
        The heavy Vosk Model is reused from self._vosk_model.
        """
        if not self._vosk_model:
            return {"text": "", "language": self.language, "confidence": 0.0}

        from vosk import KaldiRecognizer
        # KaldiRecognizer must be re-created per utterance (by Vosk design)
        rec = KaldiRecognizer(self._vosk_model, SAMPLE_RATE)

        pa     = pyaudio.PyAudio()
        stream = pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )

        logger.info("Listening for command...")
        print("[STT] Sun raha hoon... (ruk jaane par band hoga)")

        # Tunable VAD params (configurable)
        silence_timeout = float(self.config.get("silence_timeout", DEFAULT_SILENCE_TIMEOUT))
        base_threshold = float(self.config.get("silence_threshold", DEFAULT_SILENCE_THRESHOLD))

        silent_chunks    = 0
        idle_chunks      = 0
        max_silence_chunks = int(SAMPLE_RATE * silence_timeout / CHUNK_SIZE)
        max_idle_chunks    = int(SAMPLE_RATE * idle_timeout_seconds / CHUNK_SIZE) if idle_timeout_seconds else 0
        
        speech_started   = False
        text_result      = ""
        adaptive_threshold = base_threshold
        ambient_samples = []

        try:
            while True:
                data   = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                energy = _rms(data)

                if rec.AcceptWaveform(data):
                    partial = json.loads(rec.Result())
                    if partial.get("text"):
                        text_result += " " + partial["text"]

                # Build a quick ambient baseline before speech starts (for adaptive threshold)
                if not speech_started and len(ambient_samples) < 8:
                    ambient_samples.append(energy)
                    if len(ambient_samples) == 8:
                        avg_ambient = sum(ambient_samples) / len(ambient_samples)
                        adaptive_threshold = max(base_threshold, avg_ambient * 3.0)

                if energy > adaptive_threshold:
                    speech_started = True
                    silent_chunks  = 0
                else:
                    if speech_started:
                        silent_chunks += 1
                    else:
                        idle_chunks += 1

                if speech_started and silent_chunks >= max_silence_chunks:
                    break
                    
                if max_idle_chunks and not speech_started and idle_chunks >= max_idle_chunks:
                    break

        except Exception as e:
            logger.error(f"STT listening error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        # Flush remaining audio
        try:
            final_res = json.loads(rec.FinalResult())
            if final_res.get("text"):
                text_result += " " + final_res["text"]
        except Exception:
            pass

        text_result = text_result.strip().lower()
        if text_result:
            print(f"[STT] Suna: '{text_result}'")
            return {"text": text_result, "language": self.language, "confidence": 0.9}
        else:
            return {"text": "", "language": self.language, "confidence": 0.0}

    def switch_language(self, lang: str):
        """Hot-switch between 'hi' and 'en' at runtime."""
        if lang == self.language:
            return
        self.language = lang
        self.active_model_path = (
            self.model_path_hi if lang == "hi" else self.model_path_en
        )
        logger.info(f"Switching STT language to '{lang}', reloading model...")
        self._vosk_model = None
        self._load_model()

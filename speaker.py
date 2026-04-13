import threading
import queue
import logging
import os
import tempfile

import pythoncom  # Added to prevent CoInitialize error in thread

logger = logging.getLogger("Lucky.Speaker")

# FIX #7 — bounded queue prevents unbounded TTS backlog
_QUEUE_MAX_SIZE = 5


class Speaker:
    def __init__(self, config: dict):
        self.config  = config
        # maxsize=_QUEUE_MAX_SIZE: if queue is full, discard oldest item (non-blocking put)
        self.queue   = queue.Queue(maxsize=_QUEUE_MAX_SIZE)
        self.thread  = threading.Thread(
            target=self._worker, daemon=True, name="SpeakerThread"
        )
        self.running = True
        self._backend = (self.config.get("tts_backend", "") or "").strip().lower()  # "edge" | "sapi" | ""
        self.thread.start()
        logger.info("Speaker initialized.")

    # ──────────────────────────────────────────
    # Worker thread
    # ──────────────────────────────────────────

    def _worker(self):
        # Initialize COM for this thread so that SAPI5 doesn't crash
        pythoncom.CoInitialize()

        # Decide backend (prefer Edge TTS if available)
        edge_available = False
        try:
            import edge_tts  # noqa: F401
            edge_available = True
        except Exception:
            edge_available = False

        use_edge = edge_available and (self._backend in ("", "edge"))

        sapi_engine = None
        if not use_edge:
            try:
                import pyttsx3
                sapi_engine = pyttsx3.init("sapi5")
                sapi_engine.setProperty("rate", int(self.config.get("sapi_rate", 170)))
                sapi_engine.setProperty("volume", float(self.config.get("sapi_volume", 0.95)))

                voices = sapi_engine.getProperty("voices")
                preferred = (self.config.get("sapi_voice_hint", "Hindi") or "Hindi").lower()
                selected = None
                for v in voices:
                    if preferred in (v.name or "").lower() or preferred in (v.id or "").lower():
                        selected = v
                        break
                if not selected and voices:
                    selected = voices[0]
                    logger.warning("Preferred voice not found, using default SAPI voice.")
                if selected:
                    sapi_engine.setProperty("voice", selected.id)
            except Exception as e:
                logger.error(f"SAPI TTS init failed: {e}")
                sapi_engine = None

        while self.running:
            try:
                text = self.queue.get(timeout=1.0)
                if text:
                    logger.debug(f"Speaking: {text}")
                    if use_edge:
                        self._speak_edge(text)
                    elif sapi_engine:
                        sapi_engine.say(text)
                        sapi_engine.runAndWait()
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS Error: {e}")

    def _speak_edge(self, text: str):
        """
        Edge neural TTS (much smoother).
        We synthesize a short WAV file and play it synchronously.
        """
        try:
            import asyncio
            import winsound
            import edge_tts

            voice = (self.config.get("edge_voice") or "").strip() or "hi-IN-SwaraNeural"
            rate = (self.config.get("edge_rate") or "").strip() or "+0%"
            volume = (self.config.get("edge_volume") or "").strip() or "+0%"

            # Use a temp wav; winsound plays wav reliably on Windows.
            fd, wav_path = tempfile.mkstemp(prefix="lucky_tts_", suffix=".wav")
            os.close(fd)

            async def _run():
                communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, volume=volume)
                await communicate.save(wav_path)

            asyncio.run(_run())
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)
        except Exception as e:
            logger.error(f"Edge TTS failed, falling back to SAPI if available: {e}")
            try:
                import pyttsx3
                engine = pyttsx3.init("sapi5")
                engine.say(text)
                engine.runAndWait()
            except Exception:
                pass
        finally:
            try:
                if 'wav_path' in locals() and os.path.exists(wav_path):
                    os.remove(wav_path)
            except Exception:
                pass

    # ──────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────

    def speak(self, text: str):
        """
        Enqueue text for TTS.
        FIX #7: If queue is full, drop the OLDEST item first, then enqueue new one.
        This ensures responses stay fresh and relevant.
        """
        if not text:
            return
        try:
            self.queue.put_nowait(text)
        except queue.Full:
            # Drop oldest, make room for new (more relevant) response
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                pass
            try:
                self.queue.put_nowait(text)
            except queue.Full:
                logger.warning(f"TTS queue still full, discarding: {text[:30]}")

    def notify_intent(self, intent: str, entity=None):
        """Reply to the user based on what action was taken."""
        responses = {
            "LOCK_SCREEN":      "Ji, laptop lock kar diya.",
            "UNLOCK_SCREEN":    "Ji, unlock ho gaya.",
            "SLEEP":            "Ji, laptop sleep mode mein ja raha hai.",
            "SHUTDOWN":         "Theek hai, 10 second mein shutdown hoga.",
            "RESTART":          "Restart ho raha hai.",

            "OPEN_APP":         f"Ji, {entity} khol diya."     if entity else "Ji, app khol diya.",
            "CLOSE_APP":        f"Ji, {entity} band kar diya." if entity else "Ji, app band kar diya.",

            "OPEN_WEBSITE":     f"Ji, {entity} khol diya."     if entity else "Ji, website khol diya.",
            "GOOGLE_SEARCH":    f"Google pe '{entity}' search kar raha hoon." if entity else "Google pe search kar raha hoon.",
            "GEMINI_WEB_SEARCH": f"Gemini pe '{entity}' search kar raha hoon." if entity else "Gemini pe search kar raha hoon.",
            "YOUTUBE_SEARCH":   f"YouTube pe '{entity}' dhundh raha hoon."   if entity else "YouTube pe search kar raha hoon.",
            "PLAY_MUSIC":       f"Ji, YouTube pe '{entity}' baja raha hoon." if entity else "Ji, gana baja raha hoon.",

            "OPEN_FOLDER":      f"Ji, {entity} folder khol diya." if entity else "Ji, folder khol diya.",
            "NEW_FOLDER":       "Ji, naya folder bana diya Desktop pe.",

            "VOLUME_UP":        "Volume badh gayi.",
            "VOLUME_DOWN":      "Volume kam kar di.",
            "SET_VOLUME":       f"Volume {entity} percent par set kar di." if entity else "Volume set kar di.",
            "MUTE":             "Awaz mute kar di.",
            "UNMUTE":           "Awaz unmute kar di.",

            "BRIGHTNESS_UP":    "Brightness badha di.",
            "BRIGHTNESS_DOWN":  "Brightness kam kar di.",
            "SET_BRIGHTNESS":   f"Brightness {entity} percent par set kar di." if entity else "Brightness set kar di.",

            "SCREENSHOT":       "Screenshot le liya, Desktop pe save ho gayi.",

            "TIMER_SET":        f"Ji, {entity} minute ka timer lag gaya." if entity else "Ji, timer lag gaya.",
            "ALARM_SET":        f"Ji, {entity} baje alarm lag gaya."       if entity else "Ji, alarm lag gaya.",
            "REMINDER_SET":     f"Ji, {entity} baje yaad dila dunga."      if entity else "Ji, reminder set ho gaya.",

            "WIFI_ON":          "Ji, WiFi on kar diya.",
            "WIFI_OFF":         "Ji, WiFi band kar diya.",
            "BLUETOOTH_ON":     "Ji, Bluetooth on kar diya.",
            "BLUETOOTH_OFF":    "Ji, Bluetooth band kar diya.",

            "COPY":             "Copy ho gaya.",
            "PASTE":            "Paste ho gaya.",
            "UNDO":             "Undo ho gaya.",
            "REDO":             "Redo ho gaya.",
            "MINIMIZE_ALL":     "Sab windows minimize kar diye.",
            "CLOSE_TAB":        "Tab band kar diya.",
            "NEXT_TAB":         "Agla tab.",
            "PREV_TAB":         "Pichla tab.",
            "REMOVE":           "Ji, hata diya.",
            "SCROLL_UP":        "Ji, upar scroll kar diya.",
            "SCROLL_DOWN":      "Ji, neeche scroll kar diya.",
            "DICTATE":          "Ji, likh diya.",
            
            "AI_CHAT":          str(entity) if entity else "",

            "PLAY_PAUSE":       "Ji, play pause ho gaya.",
            "NEXT_TRACK":       "Agla gaana.",
            "PREV_TRACK":       "Pichla gaana.",

            "UNKNOWN":          "Yeh command mujhe nahi pata, dobara bolen.",
            "ERROR":            "Maafi chahta hun, yeh kaam nahi ho saka. Admin permission chahiye ho sakti hai.",
        }
        reply = responses.get(intent, "")
        if reply:
            self.speak(reply)

    def stop(self):
        self.running = False

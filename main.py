"""
main.py — Application Entry Point V2 (Refactored)
"""
import ctypes
# Fix DPI scaling issues for PyAutoGUI
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler
from PIL import Image, ImageDraw
import pystray
import atexit

from wake_word import WakeWordDetector
from speech_to_text import SpeechRecognizer
from intent_parser import IntentParser
from speaker import Speaker

from actions import system, apps, volume, media, browser, files, wifi_bt, shortcuts, reminders, ai_chat
import settings_gui


# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────

def setup_logging():
    # Force standard output to support UTF-8 for Emojis/Hindi on Windows
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr is not None:
        sys.stderr.reconfigure(encoding='utf-8')

    log_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
    )
    file_handler = RotatingFileHandler(
        "lucky.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)

    root_logger = logging.getLogger("Lucky")
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    return root_logger


logger = None  # Initialized in __main__

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

CONFIG_FILE = "config.json"


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        logger.error("config.json not found! Creating default...")
        default = {
            "mode": "advanced",  # "simple" or "advanced"
            "wake_word_threshold": 0.5,
            "language": "hi",
            "beep_sound": True,
            "lock_password_hash": "",
            "run_on_startup": False,
            "debug_mode": False,
            "gemini_api_key": "",
            "instant_ack": True,
            "custom_commands": {},
            "app_aliases": {
                "chrome":      "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "notepad":     "notepad.exe",
                "calculator":  "calc.exe",
                "spotify":     "spotify.exe",
                "vlc":         "vlc.exe",
                "explorer":    "explorer.exe",
                "vscode":      "code.exe"
            }
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        # Ensure new keys exist for older configs
        cfg.setdefault("mode", "advanced")
        cfg.setdefault("instant_ack", True)
        return cfg


def _is_simple_mode(config: dict) -> bool:
    return (config.get("mode", "advanced") or "advanced").strip().lower() == "simple"


def set_autostart(enable: bool = True):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            # Generate the correct python executable path for background execution
            executable = sys.executable
            if executable.endswith("python.exe"):
                # Use pythonw to prevent a black CMD window from popping up on startup
                executable = executable.replace("python.exe", "pythonw.exe")
            
            script_path = os.path.abspath(sys.argv[0])
            c_dir = os.path.dirname(script_path)
            
            # The command switches directory first, then runs pythonw so config json and paths work
            cmd = f'cmd /c cd /d "{c_dir}" && "{executable}" "{script_path}"'
            winreg.SetValueEx(key, "LuckyVoiceController", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "LuckyVoiceController")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        logger.error(f"Failed to config autostart: {e}")


# ─────────────────────────────────────────────
# FIX #9 — Dict dispatch routing table
# ─────────────────────────────────────────────

def _build_dispatch(config: dict) -> dict:
    """
    Returns a routing table:
        intent_str → callable(entity) → (success: bool, routed_entity)

    Using lambdas keeps everything lazy — no code runs until invoked.
    Adding a new intent = one new entry here.
    """
    base = {
        # System
        "LOCK_SCREEN":     lambda e: (True, system.lock_screen() or None),
        "UNLOCK_SCREEN":   lambda e: (True, system.unlock_screen(config) or None),
        "SLEEP":           lambda e: (True, system.sleep_system() or None),
        "SHUTDOWN":        lambda e: (True, system.shutdown() or None),
        "RESTART":         lambda e: (True, system.restart() or None),

        # Apps
        "OPEN_APP":        lambda e: (apps.open_app(e, config),  e),
        "CLOSE_APP":       lambda e: (apps.close_app(e),         e),

        # Browser
        "OPEN_WEBSITE":    lambda e: (browser.open_website(e, config), e),
        "GOOGLE_SEARCH":   lambda e: (True, browser.google_search(e) or e),
        "GEMINI_WEB_SEARCH": lambda e: (True, browser.gemini_web_search(e) or e),
        "YOUTUBE_SEARCH":  lambda e: (True, browser.youtube_search(e) or e),
        "PLAY_MUSIC":      lambda e: (True, browser.youtube_search(e) or e),

        # Files
        "OPEN_FOLDER":     lambda e: (files.open_folder(e), e),
        "NEW_FOLDER":      lambda e: (files.create_folder(e), e),
        "SCREENSHOT":      lambda e: (files.take_screenshot(), None),

        # Volume
        "VOLUME_UP":       lambda e: (True, volume.volume_up()),
        "VOLUME_DOWN":     lambda e: (True, volume.volume_down()),
        "SET_VOLUME":      lambda e: (True, volume.set_volume(e) or e),
        "MUTE":            lambda e: (True, volume.mute()),
        "UNMUTE":          lambda e: (True, volume.unmute()),

        # Brightness
        "BRIGHTNESS_UP":   lambda e: (True, volume.brightness_up()),
        "BRIGHTNESS_DOWN": lambda e: (True, volume.brightness_down()),
        "SET_BRIGHTNESS":  lambda e: (True, volume.set_brightness(e) or e),

        # WiFi / Bluetooth
        "WIFI_ON":         lambda e: (wifi_bt.toggle_wifi(True),      None),
        "WIFI_OFF":        lambda e: (wifi_bt.toggle_wifi(False),     None),
        "BLUETOOTH_ON":    lambda e: (wifi_bt.toggle_bluetooth(True), None),
        "BLUETOOTH_OFF":   lambda e: (wifi_bt.toggle_bluetooth(False),None),

        # Shortcuts
        "COPY":            lambda e: (shortcuts.execute_shortcut("COPY"),         None),
        "PASTE":           lambda e: (shortcuts.execute_shortcut("PASTE"),        None),
        "UNDO":            lambda e: (shortcuts.execute_shortcut("UNDO"),         None),
        "REDO":            lambda e: (shortcuts.execute_shortcut("REDO"),         None),
        "MINIMIZE_ALL":    lambda e: (shortcuts.execute_shortcut("MINIMIZE_ALL"), None),
        "MAXIMIZE_ALL":    lambda e: (shortcuts.execute_shortcut("MAXIMIZE_ALL"), None),
        "CLOSE_TAB":       lambda e: (shortcuts.execute_shortcut("CLOSE_TAB"),    None),
        "NEXT_TAB":        lambda e: (shortcuts.execute_shortcut("NEXT_TAB"),     None),
        "PREV_TAB":        lambda e: (shortcuts.execute_shortcut("PREV_TAB"),     None),
        "REMOVE":          lambda e: (shortcuts.execute_shortcut("REMOVE"),       None),
        "SCROLL_UP":       lambda e: (shortcuts.execute_shortcut("SCROLL_UP"),     None),
        "SCROLL_DOWN":     lambda e: (shortcuts.execute_shortcut("SCROLL_DOWN"),   None),
        "DICTATE":         lambda e: (True, shortcuts.dictate(e) or e),

        # Media controls
        "PLAY_PAUSE":      lambda e: (True, media.play_pause() or None),
        "NEXT_TRACK":      lambda e: (True, media.next_track() or None),
        "PREV_TRACK":      lambda e: (True, media.prev_track() or None),

        # AI
        "AI_CHAT":         lambda e: (True, ai_chat.ask_gemini(e, config)),
    }

    # Simple mode = daily commands only (no risky/admin/AI routing)
    if _is_simple_mode(config):
        allowed = {
            # Safe daily
            "LOCK_SCREEN",
            "SLEEP",

            "OPEN_APP",
            "CLOSE_APP",

            "OPEN_WEBSITE",
            "GOOGLE_SEARCH",
            "GEMINI_WEB_SEARCH",
            "YOUTUBE_SEARCH",
            "PLAY_MUSIC",

            "OPEN_FOLDER",
            "NEW_FOLDER",
            "SCREENSHOT",

            "VOLUME_UP",
            "VOLUME_DOWN",
            "SET_VOLUME",
            "MUTE",
            "UNMUTE",

            "BRIGHTNESS_UP",
            "BRIGHTNESS_DOWN",
            "SET_BRIGHTNESS",

            "PLAY_PAUSE",
            "NEXT_TRACK",
            "PREV_TRACK",

            "COPY",
            "PASTE",
            "UNDO",
            "REDO",
            "MINIMIZE_ALL",
            "MAXIMIZE_ALL",
            "CLOSE_TAB",
            "NEXT_TAB",
            "PREV_TAB",
            "REMOVE",
            "SCROLL_UP",
            "SCROLL_DOWN",
            "DICTATE",
        }
        return {k: v for k, v in base.items() if k in allowed}

    return base


# ─────────────────────────────────────────────
# Main Controller
# ─────────────────────────────────────────────

class LuckyController:
    def __init__(self):
        print("\n=== LUCKY V2 INITIALIZING ===\n")
        self.config = load_config()

        if not self.config.get("lock_password_hash"):
            system.setup_password(self.config)

        settings_gui.logger = logger

        self.speaker      = Speaker(self.config)
        self.stt          = SpeechRecognizer(self.config)
        self.parser       = IntentParser(self.config)
        self.wake_detector = WakeWordDetector(self.config, self.on_wake_word)

        # Background reminder daemon
        self.alarm_daemon = reminders.AlarmDaemon(reminders.ACTIVE_RECORDS, self.speaker)
        self.alarm_daemon.start()

        # FIX #9 — Build dispatch table at init (config captured via closure)
        self._dispatch = _build_dispatch(self.config)

        self.is_listening = True
        self.tray_icon    = None
        self._last_ack_time = 0.0

    def _maybe_instant_ack(self):
        """
        Perceived smoothness: speak a tiny acknowledgement immediately after STT finishes,
        while the command is being processed/executed.
        """
        try:
            import time
            if not self.config.get("instant_ack", True):
                return

            now = time.time()
            # Debounce so we don't spam acknowledgements back-to-back.
            if now - self._last_ack_time < 1.5:
                return
            self._last_ack_time = now

            ack = (self.config.get("instant_ack_text") or "").strip()
            if not ack:
                # Keep it super short for smoothness
                ack = "Haan."
            self.speaker.speak(ack)
        except Exception:
            pass

    def _confirm_dangerous_action(self) -> bool:
        try:
            self.speaker.speak("Ye action risky hai. Confirm karne ke liye haan bolo, cancel ke liye nahi.")
            res = self.stt.listen_and_transcribe(idle_timeout_seconds=6)
            ans = (res.get("text", "") or "").lower().strip()
            if any(w in ans for w in ["haan", "han", "yes", "confirm", "ok", "kar do", "kardo"]):
                return True
            return False
        except Exception:
            return False

    # ──────────────────────────────────────────
    # Wake word callback
    # ──────────────────────────────────────────

    def on_wake_word(self):
        if not self.is_listening:
            return

        import time
        CONTINUOUS_MINUTES = 2
        timeout_seconds = CONTINUOUS_MINUTES * 60
        start_time = time.time()
        
        print(f"\n[LUCKY] 🟢 Conversation ON — I will listen for {CONTINUOUS_MINUTES} mins.")

        while True:
            elapsed = time.time() - start_time
            if elapsed >= timeout_seconds:
                print("\n[LUCKY] 🔴 2 mins over. Sleeping...")
                break

            remaining = timeout_seconds - elapsed
            res  = self.stt.listen_and_transcribe(idle_timeout_seconds=remaining)
            text = res.get("text", "")
            
            if not text:
                # Idle timeout reached or random invalid noise
                continue

            # Reset timer on valid speech!
            start_time = time.time()

            # Instant ack improves "smoothness" a lot
            self._maybe_instant_ack()

            parsed = self.parser.parse(text)
            intent = parsed["intent"]
            entity = parsed["entity"]
            
            # Explicit sleep command manually breaks out of the loop
            if intent == "SLEEP":
                self.speaker.notify_intent("SLEEP", None)
                print("\n[LUCKY] 🔴 Sleep command received. Sleeping...")
                break

            logger.info(f"[INTENT] '{text}' → {intent} | entity={entity}")

            # ── Special intents that need extra processing ─────────────────────
            # Timer, Alarm, Reminder pass full_text for AM/PM detection
            if intent == "TIMER":
                success = reminders.set_timer(entity)
                intent  = "TIMER_SET"
                self.speaker.notify_intent(intent, entity)
                logger.info(f"Action TIMER_SET {'SUCCESS' if success else 'FAILED'}")
                continue

            if intent in ("ALARM", "REMINDER"):
                full_text = entity.get("_full_text", text) if isinstance(entity, dict) else text
                t_str  = reminders.set_alarm(
                    target_time=entity.get("time", "0") if isinstance(entity, dict) else "0",
                    msg=entity.get("message", "")       if isinstance(entity, dict) else "",
                    full_text=full_text
                )
                out_intent = "ALARM_SET" if intent == "ALARM" else "REMINDER_SET"
                self.speaker.notify_intent(out_intent, t_str)
                logger.info(f"Action {out_intent} SUCCESS")
                continue

            if intent == "CUSTOM_COMMAND":
                self._handle_custom_command(entity)
                continue

            # ── FIX #9 — Dict dispatch for all standard intents ───────────────
            handler = self._dispatch.get(intent)
            if handler:
                try:
                    result = handler(entity)
                    # Handler returns (success, routed_entity) or just (success,)
                    if isinstance(result, tuple) and len(result) == 2:
                        success, routed_entity = result
                    else:
                        success, routed_entity = bool(result), entity

                    if success:
                        self.speaker.notify_intent(intent, routed_entity)
                    else:
                        self.speaker.notify_intent("ERROR")
                    logger.info(f"Action {intent} {'SUCCESS' if success else 'FAILED'}")
                except Exception as e:
                    logger.error(f"Action {intent} raised exception: {e}")
                    self.speaker.notify_intent("ERROR")
            else:
                # Guard: single words or very short noise → skip Gemini
                if intent == "UNKNOWN":
                    words = [w for w in text.strip().split() if len(w) > 1]
                    if len(words) < 2:
                        self.speaker.notify_intent("UNKNOWN")
                        logger.info(f"Skipping Gemini for short noise: '{text}'")
                        continue

                # If intent is entirely unknown, try Gemini router (advanced mode only)
                if (not _is_simple_mode(self.config)) and (os.getenv("GEMINI_API_KEY") or self.config.get("gemini_api_key")):
                    allowed_intents = list(self._dispatch.keys()) + ["TIMER", "ALARM", "REMINDER", "CUSTOM_COMMAND"]
                    routed = ai_chat.route_command(text, self.config, allowed_intents)
                    r_intent = routed.get("intent", "UNKNOWN")
                    r_entity = routed.get("entity", None)
                    r_conf   = float(routed.get("confidence", 0.0) or 0.0)

                    if r_intent == "AI_CHAT":
                        response = ai_chat.ask_gemini(str(r_entity or text), self.config)
                        self.speaker.speak(response)
                        continue

                    if r_intent in ("UNKNOWN", "", None) or r_conf < 0.55:
                        reply = (routed.get("reply", "") or "").strip()
                        if reply:
                            self.speaker.speak(reply)
                        else:
                            self.speaker.notify_intent("UNKNOWN")
                        continue

                    # Route to special handlers first
                    if r_intent == "TIMER":
                        success = reminders.set_timer(r_entity)
                        self.speaker.notify_intent("TIMER_SET" if success else "ERROR", r_entity)
                        continue

                    if r_intent in ("ALARM", "REMINDER"):
                        if isinstance(r_entity, dict):
                            full_text = r_entity.get("_full_text", text)
                            t_str = reminders.set_alarm(
                                target_time=r_entity.get("time", "0"),
                                msg=r_entity.get("message", ""),
                                full_text=full_text,
                            )
                        else:
                            t_str = reminders.set_alarm(target_time=str(r_entity or "0"), msg="", full_text=text)
                        out_intent = "ALARM_SET" if r_intent == "ALARM" else "REMINDER_SET"
                        self.speaker.notify_intent(out_intent, t_str)
                        continue

                    if r_intent == "CUSTOM_COMMAND":
                        self._handle_custom_command(r_entity)
                        continue

                    # Confirm dangerous actions
                    dangerous = {"SHUTDOWN", "RESTART", "UNLOCK_SCREEN"}
                    if routed.get("needs_confirm") or r_intent in dangerous:
                        if not self._confirm_dangerous_action():
                            self.speaker.speak("Theek hai, cancel kar diya.")
                            continue

                    handler2 = self._dispatch.get(r_intent)
                    if handler2:
                        try:
                            result2 = handler2(r_entity)
                            if isinstance(result2, tuple) and len(result2) == 2:
                                success2, routed_entity2 = result2
                            else:
                                success2, routed_entity2 = bool(result2), r_entity

                            if success2:
                                self.speaker.notify_intent(r_intent, routed_entity2)
                            else:
                                self.speaker.notify_intent("ERROR")
                        except Exception as e:
                            logger.error(f"Routed action {r_intent} exception: {e}")
                            self.speaker.notify_intent("ERROR")
                        continue

                self.speaker.notify_intent("UNKNOWN")
                logger.warning(f"No handler registered for intent: {intent}")

    # ──────────────────────────────────────────
    # Custom command processor
    # ──────────────────────────────────────────

    def _handle_custom_command(self, entity):
        action = self.config.get("custom_commands", {}).get(entity, "")
        if not action:
            self.speaker.notify_intent("UNKNOWN")
            return
        if action.startswith("http"):
            browser.open_website(action, self.config)
        elif action.endswith(".bat") or action.endswith(".exe"):
            os.startfile(action)
        else:
            shortcuts.dictate(action)
        self.speaker.notify_intent("DICTATE", entity)
        logger.info(f"Custom command '{entity}' executed → '{action}'")

    # ──────────────────────────────────────────
    # Tray menu helpers
    # ──────────────────────────────────────────

    def show_settings(self):
        settings_gui.open_settings()
        # Reload config + rebuild dispatch after settings change
        self.config    = load_config()
        self._dispatch = _build_dispatch(self.config)

    def toggle_listening(self, icon, item):
        self.is_listening = not item.checked

    def open_logs(self):
        os.startfile("lucky.log")

    def list_timers(self):
        msg = f"Active Jobs: {len(reminders.ACTIVE_RECORDS)}"
        try:
            from plyer import notification
            notification.notify(title="Lucky Tracking", message=msg)
        except Exception:
            pass

    def exit_app(self):
        logger.info("Exiting Lucky...")
        self.wake_detector.stop()
        self.speaker.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        os._exit(0)

    # ──────────────────────────────────────────
    # Tray icon
    # ──────────────────────────────────────────

    def create_tray_icon(self):
        img = Image.new("RGB", (64, 64), color=(10, 10, 30))
        d   = ImageDraw.Draw(img)
        d.ellipse([4, 4, 60, 60], fill=(0, 180, 80))
        d.text((20, 18), "L2", fill=(255, 255, 255))

        menu = pystray.Menu(
            pystray.MenuItem("Lucky Settings",        self.show_settings),
            pystray.MenuItem("Active Timers/Alarms",  self.list_timers),
            pystray.MenuItem("View Logs",             self.open_logs),
            pystray.MenuItem(
                "Pause Listening",
                self.toggle_listening,
                checked=lambda item: not self.is_listening
            ),
            pystray.MenuItem("Exit", self.exit_app)
        )
        self.tray_icon = pystray.Icon("Lucky", img, "Lucky Voice Controller v2", menu)
        self.tray_icon.run()

    # ──────────────────────────────────────────
    # Run
    # ──────────────────────────────────────────

    def run(self):
        logger.info("Starting Lucky Controller v2...")
        self.wake_detector.start()

        if "--setup" in sys.argv:
            print("Setup run completed.")
            self.exit_app()

        if self.config.get("run_on_startup"):
            set_autostart(True)

        self.create_tray_icon()


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Primary single-instance guard (more reliable than win32 mutex alone)
    import socket as _socket
    _LOCK_SOCKET = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    try:
        _LOCK_SOCKET.bind(("127.0.0.1", 47474))
    except OSError:
        print("[Lucky] Already running! Pehle wala instance band karo.")
        sys.exit(0)

    # Prevent multiple Lucky instances (mic conflicts make it look "not listening")
    _mutex_handle = None
    try:
        import win32event
        import win32api
        import winerror

        _mutex_handle = win32event.CreateMutex(None, False, "Global\\LuckyVoiceControllerMutex")
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            print("Lucky is already running. Please close the existing tray instance first.")
            sys.exit(0)

        def _release_mutex():
            try:
                if _mutex_handle:
                    win32api.CloseHandle(_mutex_handle)
            except Exception:
                pass

        atexit.register(_release_mutex)
    except Exception:
        # If pywin32 is missing or mutex fails, continue without single-instance protection.
        pass

    logger = setup_logging()
    app = LuckyController()
    try:
        app.run()
    except KeyboardInterrupt:
        app.exit_app()

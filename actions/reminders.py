"""
reminders.py — Timer, Alarm & Reminder System V2
=================================================
Fixes:
- [#2] Typo: "Timer amapt" → "Timer ho gaya"
- [#3] ACTIVE_RECORDS persisted to reminders.json (survive restarts)
- [#4] AM/PM parsing: 'subah', 'dopahar', 'shaam', 'raat' support
"""

import threading
import datetime
import json
import os
import logging
from plyer import notification

logger = logging.getLogger("Lucky.Actions.Reminders")

REMINDERS_FILE = "reminders.json"
ACTIVE_RECORDS = []  # Shared in-memory list (also backed by reminders.json)


# ─────────────────────────────────────────────
# Persistence helpers
# ─────────────────────────────────────────────

def _save_records():
    """Persist only alarm/reminder jobs (timers are fire-and-forget)."""
    try:
        persistent = [j for j in ACTIVE_RECORDS if j.get("type") in ("alarm", "reminder")]
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(persistent, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved {len(persistent)} records to {REMINDERS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save reminders: {e}")


def _load_records():
    """Load persisted alarm/reminder jobs from disk on startup."""
    global ACTIVE_RECORDS
    if not os.path.exists(REMINDERS_FILE):
        return
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Only load jobs whose target_time hasn't passed yet
        now = datetime.datetime.now()
        valid = []
        for job in data:
            try:
                t = datetime.datetime.strptime(job["target_time"], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                # If time already passed today, skip stale job
                if t > now:
                    valid.append(job)
                else:
                    logger.info(f"Dropped stale job '{job}' that already passed.")
            except Exception:
                pass
        ACTIVE_RECORDS.extend(valid)
        logger.info(f"Loaded {len(valid)} active reminder(s) from disk.")
    except Exception as e:
        logger.error(f"Failed to load reminders: {e}")


# Load on import
_load_records()


# ─────────────────────────────────────────────
# Sound helpers
# ─────────────────────────────────────────────

def _play_alarm_sound():
    try:
        import winsound
        for _ in range(3):
            winsound.Beep(1000, 500)
    except Exception:
        pass


# ─────────────────────────────────────────────
# Timer
# ─────────────────────────────────────────────

def _timer_callback(minutes: int):
    """Called when timer fires."""
    _play_alarm_sound()
    try:
        notification.notify(
            title="Lucky Timer",
            message=f"Timer ho gaya! {minutes} minute(s) puri ho gayi.",  # FIX #2
            app_name="Lucky Assistant"
        )
    except Exception:
        pass
    logger.info(f"Timer completed: {minutes}m")


def set_timer(minutes: int) -> bool:
    if not minutes:
        return False
    seconds = minutes * 60
    t = threading.Timer(seconds, _timer_callback, [minutes])
    t.daemon = True
    t.start()
    ACTIVE_RECORDS.append({
        "type": "timer",
        "minutes": minutes,
        "time": datetime.datetime.now().strftime("%H:%M")
    })
    # Timers are NOT persisted (fire-and-forget), but we note them in-memory
    logger.info(f"Set timer for {minutes} minute(s).")
    return True


# ─────────────────────────────────────────────
# AM/PM time parser (FIX #4)
# ─────────────────────────────────────────────

def _parse_time_string(raw_hour: str, full_text: str = "") -> str:
    """
    Convert a raw hour string + context to HH:MM format.

    Supports Hinglish modifiers:
      subah / morning  → AM  (6–11)
      dopahar          → noon (12)
      shaam / evening  → PM  (5–8 range)
      raat / night     → PM  (8–11 range + 12+ mapped to 0)

    If no modifier is given, heuristic:
      <= 5 → PM  (assume evening)
      6-11 → AM
      12   → noon
    """
    text_lower = full_text.lower() if full_text else ""
    try:
        hour = int(raw_hour)
    except (ValueError, TypeError):
        return "00:00"

    # Explicit period modifiers
    if any(w in text_lower for w in ["subah", "morning", "savere"]):
        # Keep as AM; clamp to 00-11
        hour = hour % 12
    elif any(w in text_lower for w in ["dopahar", "noon", "dopher"]):
        hour = 12 if hour != 12 else 12
    elif any(w in text_lower for w in ["shaam", "evening", "sham"]):
        hour = hour if hour == 12 else hour + 12
        if hour >= 24:
            hour = hour % 24
    elif any(w in text_lower for w in ["raat", "night", "ratra"]):
        if hour == 12:
            hour = 0
        elif hour < 12:
            hour = hour + 12
        if hour >= 24:
            hour = hour % 24
    else:
        # Heuristic: 1-5 → PM (evening), 6-11 → AM, 12 → PM
        if 1 <= hour <= 5:
            hour = hour + 12
        elif hour == 12:
            pass  # noon, stays 12

    return f"{hour:02d}:00"


# ─────────────────────────────────────────────
# AlarmDaemon — background polling (FIX #3)
# ─────────────────────────────────────────────

class AlarmDaemon(threading.Thread):
    def __init__(self, globals_ref, speaker):
        super().__init__(daemon=True, name="AlarmDaemon")
        self.speaker = speaker
        self.jobs = globals_ref

    def run(self):
        import time
        while True:
            now = datetime.datetime.now().strftime("%H:%M")
            fired_jobs = []
            for job in list(self.jobs):
                if job.get("type") in ["alarm", "reminder"]:
                    if job.get("target_time") == now:
                        _play_alarm_sound()
                        msg = job.get("msg", "Alarm baj raha hai!")
                        try:
                            notification.notify(
                                title="Lucky Assistant",
                                message=msg,
                                app_name="Lucky Assistant"
                            )
                        except Exception:
                            pass

                        if job["type"] == "reminder":
                            self.speaker.speak(f"Yaad dilana tha: {msg}")
                        else:
                            self.speaker.speak("Alarm baj gaya hai!")

                        fired_jobs.append(job)

            # Remove fired jobs and save updated state (FIX #3)
            for job in fired_jobs:
                try:
                    self.jobs.remove(job)
                except ValueError:
                    pass
            if fired_jobs:
                _save_records()

            time.sleep(30)  # poll every 30 seconds


# ─────────────────────────────────────────────
# Public set functions
# ─────────────────────────────────────────────

def set_alarm(target_time: str, msg: str = "", full_text: str = "") -> str:
    """
    Set an alarm.
    target_time: raw hour string, e.g. '5' or '17:00'
    msg: optional message
    full_text: original user command (for AM/PM detection)
    """
    # If already HH:MM format, use directly
    if isinstance(target_time, str) and len(target_time) == 5 and ":" in target_time:
        t_str = target_time
    else:
        t_str = _parse_time_string(str(target_time), full_text)

    job_type = "reminder" if msg else "alarm"
    job = {
        "type": job_type,
        "target_time": t_str,
        "msg": msg or f"Alarm baj raha hai! ({t_str})"
    }
    ACTIVE_RECORDS.append(job)
    _save_records()  # FIX #3 — persist immediately
    logger.info(f"Set {job_type} at {t_str} | msg='{msg}'")
    return t_str

"""
intent_parser.py — Intent Classification V2 (Fixed)
=====================================================
Fixes:
- [#6]  Entity extraction uses split-based approach instead of naive str.replace()
        which was corrupting multi-word entities.
- [#10] Added English phrases alongside Hindi in INTENTS dict.
"""

from rapidfuzz import process, fuzz
import logging
import re
import random

logger = logging.getLogger("Lucky.Intent")

# ─────────────────────────────────────────────
# Intent phrase database (Hindi + English)
# ─────────────────────────────────────────────

INTENTS = {
    "LOCK_SCREEN": [
        "lock karo", "laptop band karo", "screen lock", "lock it", "lock screen", "lock kar do",
        "लॉक करो", "लैपटॉप बंद करो", "स्क्रीन लॉक", "लॉक कर दो"
    ],
    "UNLOCK_SCREEN": [
        "unlock", "unlock karo", "unlock screen", "unlock kar do",
        "अनलॉक", "अनलॉक करो", "अनलॉक कर दो"
    ],
    "SLEEP": [
        "so jao", "sleep mode", "laptop sulao", "sleep karo", "sleep",
        "सो जाओ", "स्लीप मोड", "स्लीप करो"
    ],
    "VOLUME_UP": [
        "volume badha", "louder", "aawaz badha", "volume up", "increase volume", "thoda louder karo",
        "वॉल्यूम बढ़ाओ", "वॉल्यूम ज्यादा", "आवाज बढ़ाओ", "आवाज तेज करो"
    ],
    "VOLUME_DOWN": [
        "volume ghatao", "quiet karo", "aawaz kam karo", "volume down", "decrease volume", "volume kam karo",
        "वॉल्यूम घटाओ", "वॉल्यूम कम करो", "आवाज कम करो"
    ],
    "MUTE": [
        "mute karo", "sound band karo", "mute", "silence",
        "म्यूट", "म्यूट करो", "आवाज बंद करो"
    ],
    "UNMUTE": [
        "unmute", "awaaz chalu karo", "sound on karo", "unmute karo",
        "अनम्यूट", "आवाज चालू करो", "अनम्यूट करो"
    ],
    "SCREENSHOT": [
        "screenshot le", "screenshot lo", "capture karo", "take screenshot", "screen capture",
        "स्क्रीनशॉट", "स्क्रीनशॉट लो", "स्क्रीनशॉट ले लो"
    ],
    "SHUTDOWN": [
        "shutdown karo", "computer band karo", "shut down", "turn off computer",
        "शटडाउन", "शटडाउन करो", "कंप्यूटर बंद करो"
    ],
    "RESTART": [
        "restart karo", "reboot karo", "restart", "reboot my computer",
        "रीस्टार्ट", "रीस्टार्ट करो", "सिस्टम रिस्टार्ट करें", "सिस्टम रिस्टार्ट", "रिस्टार्ट करो"
    ],
    "BRIGHTNESS_UP": [
        "brightness badha", "screen roshan karo", "brightness up", "increase brightness", "brightness badhao",
        "ब्राइटनेस बढ़ाओ", "ब्राइटनेस तेज करो"
    ],
    "BRIGHTNESS_DOWN": [
        "dim karo", "brightness kam karo", "brightness down", "decrease brightness", "brightness ghatao",
        "ब्राइटनेस घटाओ", "ब्राइटनेस कम करो"
    ],
    "NEW_FOLDER": [
        "naya folder banao", "new folder", "create folder",
        "naya folder create karo", "folder banao", "desktop folder banao", "desktop par folder banao",
        "नया फोल्डर", "नया फोल्डर बनाओ", "फोल्डर बनाओ"
    ],
    "WIFI_ON": [
        "wifi on karo", "wifi chalu karo", "wifi on", "turn on wifi",
        "वाईफाई ऑन", "वाईफाई चालू करो"
    ],
    "WIFI_OFF": [
        "wifi band karo", "wifi off", "turn off wifi",
        "वाईफाई बंद", "वाईफाई बंद करो"
    ],
    "BLUETOOTH_ON": [
        "bluetooth on karo", "bluetooth on", "turn on bluetooth",
        "ब्लूटूथ ऑन", "ब्लूटूथ चालू करो"
    ],
    "BLUETOOTH_OFF": [
        "bluetooth band karo", "bluetooth off", "turn off bluetooth",
        "ब्लूटूथ बंद", "ब्लूटूथ बंद करो"
    ],
    "COPY": [
        "copy karo", "copy", "ctrl c", "copy this",
        "कॉपी", "कॉपी करो"
    ],
    "PASTE": [
        "paste karo", "paste", "ctrl v", "paste this",
        "पेस्ट", "पेस्ट करो"
    ],
    "UNDO": [
        "undo karo", "undo", "piche jao", "wapas karo",
        "अंडू", "अंडू करो", "पीछे जाओ"
    ],
    "REDO": [
        "redo karo", "redo", "aage jao",
        "रीडू", "रीडू करो", "आगे जाओ"
    ],
    "MINIMIZE_ALL": [
        "sab windows minimize karo", "desktop dikha", "sab minimize karo", "minimize all",
        "सब मिनिमाइज करो", "डेस्कटॉप दिखाओ", "मिनिमम करो", "मिनिमम मिनिमम करो", "मिनिमाइज करो"
    ],
    "MAXIMIZE_ALL": [
        "maximum karo", "maximum", "मैक्सिमम", "मैक्सिमम करो", "maximize all", "maximize",
        "sab windows maximum karo", "restore windows"
    ],
    "CLOSE_TAB": [
        "yeh tab band karo", "last tab close karo", "tab close karo", "close this tab",
        "टैब बंद", "टैब बंद करो"
    ],
    "NEXT_TAB": [
        "agla tab", "next tab", "next tab dikhao",
        "अगला टैब"
    ],
    "PREV_TAB": [
        "pichla tab", "previous tab", "prev tab",
        "पिछला टैब"
    ],
    "PLAY_PAUSE": [
        "play pause", "pause karo", "roko", "chala do", "resume karo",
        "पॉज करो", "रोको", "चला दो", "रिज्यूम करो"
    ],
    "NEXT_TRACK": [
        "agla gaana", "next song", "next track", "skip karo",
        "अगला गाना", "नेक्स्ट सॉन्ग", "स्किप करो"
    ],
    "PREV_TRACK": [
        "pichla gaana", "previous song", "previous track",
        "पिछला गाना", "प्रीवियस सॉन्ग"
    ],
    "AI_CHAT": [
        "batao", "bata", "samjhao", "kya hai", "kya hota hai",
        "mujhe batao", "explain karo", "kaise", "kyon",
        "kya", "why", "how", "what", "samjha",
        "बताओ", "समझाओ", "क्या है", "कैसे"
    ],
    "REMOVE": [
        "remove", "hatao", "delete karo", "hata do", "backspace",
        "हटाओ", "डिलीट करो", "हटा do", "मिटाओ"
    ],
    "SCROLL_UP": [
        "scroll up", "upar karo", "upar scroll karo", "page up",
        "ऊपर करो", "ऊपर स्क्रॉल करो", "upar jaoo", "upar jao", "ऊपर जाओ"
    ],
    "SCROLL_DOWN": [
        "scroll down", "neeche karo", "neeche scroll karo", "page down",
        "नीचे करो", "नीचे स्क्रॉल करो", "niche aioo", "niche ao", "नीचे आओ"
    ]
}

# ─────────────────────────────────────────────
# Disambiguation lists
# ─────────────────────────────────────────────

KNOWN_WEBSITES = [
    "youtube", "gmail", "whatsapp", "google", "facebook",
    "instagram", "twitter", "github", "chatgpt", "claude",
    "netflix", "hotstar", "spotify", "gemini",
    "यूट्यूब", "जीमेल", "व्हाट्सएप", "गूगल", "फेसबुक", "इंस्टाग्राम", "ट्विटर", "गिटहब", "चैटजीपीटी", "क्लॉड", "नेटफ्लिक्स", "हॉटस्टार", "स्पॉटिफाई", "जेमिनी"
]
KNOWN_FOLDERS = [
    "downloads", "desktop", "documents", "pictures",
    "music", "videos", "recent files", "recent",
    "डाउनलोड", "डेस्कटॉप", "डॉक्यूमेंट", "पिक्चर्स", "म्यूजिक", "वीडियो", "रीसेंट", "रिसेंट"
]
KNOWN_SINGERS = [
    "karan aujla", "honey singh", "sidhu moose wala", "arijit singh",
    "diljit dosanjh", "shreya ghoshal", "sonu nigam", "kishore kumar",
    "lata mangeshkar", "badshah", "guru randhawa", "neha kakkar",
    "b praak", "jubin nautiyal", "himesh reshammiya", "atif aslam",
    "करण औजला", "हनी सिंह", "सिद्धू मूस वाला", "अरिजीत सिंह", "दिलजीत",
    "बादशाह"
]

# Open/Close trigger words mapped to what comes AFTER them in the sentence
APP_OPEN_KEYWORDS = ["kholo", "open", "lagao", "start", "chalao", "chalu karo", "खोलो", "खोलें", "लगाओ", "चालू करो", "ओपन", "खुला", "खोल", "खोलना"]
APP_CLOSE_KEYWORDS = ["band karo", "close", "kill", "stop", "hatao", "band kar do", "बंद करो", "बंद कर दो", "हटाओ", "बंद", "क्लोज"]


# ─────────────────────────────────────────────
# Entity extraction helpers (FIX #6)
# ─────────────────────────────────────────────

def _map_devanagari_to_english(text: str) -> str:
    """Map common Devanagari words to English so system commands work."""
    mapping = {
        "क्रोम": "chrome", "क्रॉम": "chrome", "रूम": "chrome",  # Common STT mistakes
        "गूगल": "google", "यूट्यूब": "youtube", "व्हाट्सएप": "whatsapp", "व्हाट्सएप्प": "whatsapp",
        "इंस्टाग्राम": "instagram", "फेसबुक": "facebook", "ट्विटर": "twitter",
        "गिटहब": "github", "नेटफ्लिक्स": "netflix", "जीमेल": "gmail", "चैटजीपीटी": "chatgpt",
        "नोटपैड": "notepad", "केलकुलेटर": "calculator", "स्पॉटिफाई": "spotify",
        "वीएलसी": "vlc", "एक्सप्लोरर": "explorer", "वीएस कोड": "vscode",
        "वीएस एस कोड": "vscode",
        "वी एस कोड": "vscode",
        "बी एस कोड": "vscode",
        "विजुअल स्टूडियो": "vscode",
        "डेस्कटॉप": "desktop", "डाउनलोड": "downloads", "डॉक्यूमेंट": "documents",
        "पिक्चर्स": "pictures", "म्यूजिक": "music", "वीडियो": "videos",
        "रिसाइकिल बीन": "recycle bin", "रीसायकल बिन": "recycle bin", "रिसाइकिल बिन": "recycle bin",
        "रिसाइकिलिंग": "recycle bin",
        "फोल्डर": "folder",
        "स्टार्ट": "start", "चालू": "start", "शुरू": "start", "ओपन": "open",
        "लैपटॉप": "explorer", # If user says laptop kholo
        "बोलो": "kholo", "खोलो": "kholo", "खोलें": "kholo", "खोल": "kholo", "फुले": "kholo", "खुले": "kholo",
        "हो": "kholo", "होना": "kholo", "खुल": "kholo",
        "मालूम": "volume", "वॉल्यूम": "volume", "क्लोज": "close",
        "सर्च": "search", "सच": "search", "ढूंढो": "search", "ढूंढ": "search",
        "महादेव": "mahadev", "सिक्योरिटी": "securities", "सिक्योरिटीज": "securities", "फाइल": "file",
        "कन्नौज": "karan", "कनोज": "karan", "जिला": "aujla", "औजला": "aujla",
        "vs code": "vscode", "anti gravity": "antigravity", "antigravity": "antigravity",
        "जेमिनी": "gemini"
    }
    # Sort by length descending to ensure longer matches (like 'होना') take precedence over shorter ones ('हो')
    sorted_mapping = dict(sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True))
    
    for hi, en in sorted_mapping.items():
        if hi in text:
            text = text.replace(hi, en)
    return text.strip()

def _extract_entity_after(text: str, keyword: str) -> str:
    """
    Safely extract the entity that appears AFTER a keyword.
    """
    # Use regex split to avoid splitting inside other words
    parts = re.split(fr'(?<!\S){re.escape(keyword)}(?!\S)', text, maxsplit=1)
    if len(parts) < 2:
        return ""
    after = parts[1].strip()
    # Remove trailing filler words that are NOT the entity
    # Do not use \b for Hindi because Python regex \b misbehaves with non-Latin scripts
    filler_words = ['karo', 'kar do', 'do', 'please', 'na', 'करो', 'कर दो', 'दो', 'प्लीज', 'ना']
    for fw in filler_words:
        if after.endswith(f" {fw}") or after == fw:
            after = after[:len(after) - len(fw)].strip()
    return after if after else ""

def _extract_entity_before(text: str, keyword: str) -> str:
    """
    Extract entity that appears BEFORE a keyword.
    """
    parts = re.split(fr'(?<!\S){re.escape(keyword)}(?!\S)', text, maxsplit=1)
    if not parts or len(parts) < 2:
        return ""
    before = parts[0].strip()
    filler_words = ['mujhe', 'please', 'zara', 'मुझे', 'ज़रा', 'प्लीज']
    for fw in filler_words:
        if before.startswith(f"{fw} ") or before == fw:
            before = before[len(fw):].strip()
    return before if before else ""


# ─────────────────────────────────────────────
# Main Parser
# ─────────────────────────────────────────────

class IntentParser:
    def __init__(self, config: dict):
        self.config = config

        # Flatten intents → phrase: intent
        self.choices = {}
        for intent, phrases in INTENTS.items():
            for phrase in phrases:
                self.choices[phrase] = intent

        # Load custom commands from config
        custom = self.config.get("custom_commands", {})
        for cmd, action in custom.items():
            self.choices[cmd.lower()] = "CUSTOM_COMMAND"

    def parse(self, text: str) -> dict:
        text = text.lower().strip()
        if not text:
            return {"intent": "UNKNOWN", "entity": None, "confidence": 0}
            
        # Standardize devanagari errors beforehand
        mapped_text = _map_devanagari_to_english(text)

        # ── 0. New folder with optional name (daily routine) ──────────────
        # Examples:
        #   "new folder banao notes"
        #   "naya folder banao assignment"
        #   "नया फोल्डर बनाओ नोट्स"
        if ("folder" in mapped_text) and any(t in mapped_text for t in ["new folder", "create folder", "naya folder", "folder banao"]):
            cleaned = mapped_text
            for t in ["new folder", "create folder", "naya folder", "folder banao", "desktop folder banao", "desktop par folder banao"]:
                cleaned = cleaned.replace(t, " ")
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            # If user gave a name, pass it; else None (will default to "New Folder")
            return {"intent": "NEW_FOLDER", "entity": cleaned if cleaned else None, "confidence": 0.95}

        # ── 1. Dictation ──────────────────────────────────────────────────
        for trigger in ["notepad mein likh", "yeh likh:", "yeh likh", "type this", "नोटपैड में लिखो", "यह लिखो"]:
            if trigger in text or trigger in mapped_text:
                payload = text.replace(trigger, "").strip()
                if not payload:
                    payload = mapped_text.replace(trigger, "").strip()
                return {"intent": "DICTATE", "entity": payload, "confidence": 1.0}

        # ── 2. Timer ──────────────────────────────────────────────────────
        if "timer" in text:
            match = re.search(r'(\d+)\s*minute', text)
            if match:
                return {"intent": "TIMER", "entity": int(match.group(1)), "confidence": 0.95}
            # Try plain digit: "5 ka timer"
            match = re.search(r'(\d+)', text)
            if match:
                return {"intent": "TIMER", "entity": int(match.group(1)), "confidence": 0.85}

        # ── 3. Alarm / Reminder ───────────────────────────────────────────
        if "alarm" in text or "yaad dilana" in text or "reminder" in text or "अलार्म" in text or "याद दिलाना" in text:
            time_match = re.search(r'(\d+)\s*(baje|बजे)', text)
            raw_hour   = time_match.group(1) if time_match else "0"

            if "yaad dilana" in text or "reminder" in text or "याद दिलाना" in text:
                msg_parts = re.split(r'yaad dilana|reminder (ke liye)?|याद दिलाना|रिमाइंडर', text)
                msg = msg_parts[-1].strip() if len(msg_parts) > 1 else "Reminder"
                entity_val = {"time": raw_hour, "message": msg, "_full_text": text}
                return {"intent": "REMINDER", "entity": entity_val, "confidence": 0.95}
            else:
                entity_val = {"time": raw_hour, "message": "", "_full_text": text}
                return {"intent": "ALARM", "entity": entity_val, "confidence": 0.95}

        # ── 4. Search ─────────────────────────────────────────────────────
        for trigger in ["search karo", "search kar", "search", "dhundo", "find", "सर्च करो", "ढूंढो", "सच करो"]:
            # Try matching in both original and mapped text
            matching_text = None
            if trigger in text:
                matching_text = text
            elif trigger in mapped_text:
                matching_text = mapped_text

            if matching_text:
                query = _extract_entity_after(matching_text, trigger)
                if not query:
                    query = matching_text.replace(trigger, "").strip()
                
                # Check for specific search engines
                # We check both to be safe
                if "youtube" in text or "youtube" in mapped_text:
                    return {"intent": "YOUTUBE_SEARCH", "entity": query, "confidence": 0.95}
                if "gemini" in text or "gemini" in mapped_text:
                    return {"intent": "GEMINI_WEB_SEARCH", "entity": query, "confidence": 0.95}
                return {"intent": "GOOGLE_SEARCH", "entity": query, "confidence": 0.95}

        # ── 4b. Play Music (YouTube) ──────────────────────────────────────
        play_triggers = [
            "का गाना लगाओ", "का गाना बजाओ", "का गाने लगा", "कि गाने लगा",
            "का गाने बजाओ", "के गाने बजाओ", "की गाने बजाओ", "का गाना लगा",
            "का गाना", "गाना लगाओ", "गाना बजाओ", "गाना लगा", "गाने लगा",
            "कहने लगा", "बताने लगा",
            "ka gana bajao", "ka gana lagao", "ka gaane laga", "ka gaana lagao",
            "gana bajao", "gana lagao", 
            "play song of", "play song by", "play music of", "play song", "play music", "play", 
            "bajao", "baja oo", "baja do",
            "बजाओ", "बजा दो",
        ]
        # Order by length descending to match longest phrases first
        for trigger in sorted(play_triggers, key=len, reverse=True):
            if re.search(fr'(?<!\S){re.escape(trigger)}(?!\S)', text) or re.search(fr'(?<!\S){re.escape(trigger)}(?!\S)', mapped_text):
                if trigger in ["play song of", "play song by", "play music of", "play song", "play music", "play"]:
                    query = _extract_entity_after(mapped_text, trigger)
                elif "ka " in trigger or "का " in trigger or "के " in trigger or "की " in trigger or "ki " in trigger or "ke " in trigger:
                    query = _extract_entity_before(mapped_text, trigger)
                else:
                    # 'gana bajao', 'बजाओ'
                    query = _extract_entity_before(mapped_text, trigger)
                    if not query or query in ['karo', 'kar do']:
                        query = _extract_entity_after(mapped_text, trigger)

                if not query:
                    # Clean out trigger from original text directly via regex
                    query = re.sub(fr'(?<!\S){re.escape(trigger)}(?!\S)', "", mapped_text).strip()
                
                if query:
                    # Clean out common STT hallucination words just in case
                    clean_q = re.sub(r'(?i)(youtube\s*(par|pe)?|laptop\s*(mein|me)?|please)', '', query).strip()
                    if clean_q:
                        search_term = clean_q
                        if "song" not in search_term.lower() and "gana" not in search_term.lower() and "music" not in search_term.lower():
                             search_term += " song"
                        return {"intent": "PLAY_MUSIC", "entity": search_term, "confidence": 0.95}
                
                fallback_queries = [
                    "latest hindi superhit songs",
                    "top bollywood songs",
                    "arijit singh best songs",
                    "kishore kumar hits",
                    "trending hindi lofi mashup",
                    "punjabi hit songs",
                    "old hindi classic songs",
                    "relaxing bollywood hits",
                    "karan ajula song",
                    "chemma y songs"
                ]
                return {"intent": "PLAY_MUSIC", "entity": random.choice(fallback_queries) + "::RANDOM", "confidence": 0.9}

        # ── 5. Open (app / website / folder) — FIX #6 ────────────────────
        for kw in APP_OPEN_KEYWORDS:
            if re.search(fr'(?<!\S){re.escape(kw)}(?!\S)', mapped_text):
                if kw in ["open", "start", "launch", "ओपन", "स्टार्ट"]:
                    # English syntax: "open notepad" -> Target is AFTER verb
                    target = _extract_entity_after(mapped_text, kw)
                    if not target:
                        target = _extract_entity_before(mapped_text, kw)
                else:
                    # Hindi syntax: "notepad kholo" -> Target is BEFORE verb
                    target = _extract_entity_before(mapped_text, kw)
                    if not target:
                        target = _extract_entity_after(mapped_text, kw)
                
                if not target:
                    continue

                if any(w in target for w in KNOWN_WEBSITES):
                    return {"intent": "OPEN_WEBSITE", "entity": target, "confidence": 0.95}
                if any(w in target for w in KNOWN_FOLDERS) or target == "recycle bin":
                    return {"intent": "OPEN_FOLDER", "entity": target, "confidence": 0.95}
                return {"intent": "OPEN_APP", "entity": target, "confidence": 0.90}
                
        # ── 5b. Standalone App Names (e.g. user just said "chrome" or "क्रोम") ───
        for alias in self.config.get("app_aliases", {}).keys():
            if mapped_text == alias or mapped_text == f"{alias} app":
                return {"intent": "OPEN_APP", "entity": alias, "confidence": 0.95}
        for kw in KNOWN_WEBSITES:
            if mapped_text == kw:
                return {"intent": "OPEN_WEBSITE", "entity": _map_devanagari_to_english(kw), "confidence": 0.95}
        for kw in KNOWN_FOLDERS:
            if mapped_text == kw:
                return {"intent": "OPEN_FOLDER", "entity": _map_devanagari_to_english(kw), "confidence": 0.95}
        for kw in KNOWN_SINGERS:
            if mapped_text == kw or mapped_text == f"{kw} song" or mapped_text == f"{kw} ka gana":
                return {"intent": "PLAY_MUSIC", "entity": f"{kw} song", "confidence": 0.95}

        # ── 6. Close (app) — FIX #6 ──────────────────────────────────────
        for kw in APP_CLOSE_KEYWORDS:
            if re.search(fr'(?<!\S){re.escape(kw)}(?!\S)', mapped_text):
                if kw in ["close", "kill", "stop", "क्लोज"]:
                    target = _extract_entity_after(mapped_text, kw)
                    if not target: target = _extract_entity_before(mapped_text, kw)
                else:
                    target = _extract_entity_before(mapped_text, kw)
                    if not target: target = _extract_entity_after(mapped_text, kw)
                
                if target:
                    return {"intent": "CLOSE_APP", "entity": target, "confidence": 0.95}

        # ── 7. Set Volume percent (FIX #10) ───────────────────────────────
        if "volume" in mapped_text:
            match = re.search(r'(\d+)', mapped_text)
            if match:
                return {"intent": "SET_VOLUME", "entity": int(match.group(1)), "confidence": 0.9}

        # ── 8. Set Brightness percent (FIX #10) ───────────────────────────
        if "brightness" in mapped_text or "ब्राइटनेस" in mapped_text:
            match = re.search(r'(\d+)', mapped_text)
            if match:
                return {"intent": "SET_BRIGHTNESS", "entity": int(match.group(1)), "confidence": 0.9}

        # ── 9. Fuzzy match against static intents & custom commands ───────
        best_match = process.extractOne(
            text, self.choices.keys(), scorer=fuzz.token_set_ratio
        )
        if best_match:
            match_str, score, _ = best_match
            if score > 75:
                matched_intent = self.choices[match_str]
                entity = text if matched_intent == "CUSTOM_COMMAND" else None
                return {
                    "intent": matched_intent,
                    "entity": entity,
                    "confidence": round(score / 100.0, 2)
                }

        return {"intent": "UNKNOWN", "entity": None, "confidence": 0.0}

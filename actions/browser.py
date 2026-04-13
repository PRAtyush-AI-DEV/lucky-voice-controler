import webbrowser
import logging

logger = logging.getLogger("Lucky.Actions.Browser")

HINDI_SITE_MAP = {
    "व्हाट्सएप": "whatsapp",
    "व्हाट्सएप्प": "whatsapp",
    "इंस्टाग्राम": "instagram",
    "यूट्यूब": "youtube",
    "फेसबुक": "facebook",
    "गूगल": "google",
    "जीमेल": "gmail",
    "ट्विटर": "twitter",
    "गिटहब": "github",
    "नेटफ्लिक्स": "netflix",
    "क्लॉड": "claude",
    "चैटजीपीटी": "chatgpt",
    "जेमिनी": "gemini",
}

COMMON_SITES = {
    "youtube": "https://youtube.com",
    "gmail": "https://gmail.com",
    "whatsapp": "https://web.whatsapp.com",
    "google": "https://google.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "twitter": "https://twitter.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "gemini": "https://gemini.google.com/app"
}

def open_website(site_name: str, config: dict) -> bool:
    if not site_name: return False
    site_name = site_name.strip().lower()
    # Map Hindi names to English before lookup
    site_name = HINDI_SITE_MAP.get(site_name, site_name)
    
    # 1. Check custom config websites
    custom_sites = config.get("websites", {})
    if site_name in custom_sites:
        url = custom_sites[site_name]
        webbrowser.open(url)
        logger.info(f"Opened custom site: {url}")
        return True
        
    # 2. Check common
    for key, url in COMMON_SITES.items():
        if key in site_name:
            webbrowser.open(url)
            logger.info(f"Opened known site: {url}")
            return True
            
    # 3. Fallback generic '.com' guess
    url = f"https://{site_name.replace(' ', '')}.com"
    webbrowser.open(url)
    logger.info(f"Guessed and opened site: {url}")
    return True

def google_search(query: str):
    if not query: return
    url = f"https://google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    logger.info(f"Google Search: {query}")

def youtube_search(query: str):
    if not query: return
    try:
        import urllib.request
        from urllib.parse import quote
        import re
        import random
        
        is_random = "::RANDOM" in query
        search_query = query.replace("::RANDOM", "").strip()
        
        # Search youtube and extract video IDs
        html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={quote(search_query)}")
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
        
        if video_ids:
            unique_ids = list(dict.fromkeys(video_ids))
            if is_random and len(unique_ids) > 1:
                vid = random.choice(unique_ids[:10])
            else:
                vid = unique_ids[0]
                
            url = f"https://www.youtube.com/watch?v={vid}"
            webbrowser.open(url)
            logger.info(f"YouTube Playback Auto-Started: {url}")
            return
    except Exception as e:
        logger.error(f"Failed to extract video ID: {e}")
        
    # Fallback to the search results page
    url = f"https://youtube.com/results?search_query={query.replace(' ', '+')}"
    webbrowser.open(url)
    logger.info(f"YouTube Search Fallback: {query}")

def gemini_web_search(query: str):
    if not query: return
    
    import threading
    def _run():
        import pyperclip
        import pyautogui
        import time
        import pygetwindow as gw
        
        webbrowser.open("https://gemini.google.com/app")
        # 12s wait for heavy Gemini Pro interface
        time.sleep(12)
        
        # 1. Try to activate the Gemini window to bring to foreground
        try:
            # Look for Gemini specifically
            gemini_windows = [w for w in gw.getWindowsWithTitle('') if 'Gemini' in w.title]
            if gemini_windows:
                gemini_windows[0].activate()
                time.sleep(1)
        except Exception:
            pass

        # 2. Clear potential overlays/modals with Esc
        try:
            for _ in range(3):
                pyautogui.press('esc')
                time.sleep(0.3)
        except Exception:
            pass
        
        # 3. Multiple clicks to ensure focus on the input area
        try:
            sw, sh = pyautogui.size()
            cx = sw // 2
            cy = int(sh * 0.81) # Slightly adjusted based on user screenshot
            
            # Focus window fully
            pyautogui.click(cx, cy)
            time.sleep(0.5)
            # Focus input field
            pyautogui.click(cx, cy)
            time.sleep(0.5)
            # Clear/Select
            pyautogui.click(cx, cy, clicks=2, interval=0.1)
            time.sleep(0.8)
        except Exception:
            pass
            
        # 4. Paste and Enter
        old_cb = ""
        try:
            old_cb = pyperclip.paste()
        except Exception:
            pass
            
        pyperclip.copy(query)
        # Paste via keyboard shortcut
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(1.2)
        # Final submit
        pyautogui.press('enter')
        
        # Restore old clipboard
        time.sleep(1)
        try:
            pyperclip.copy(old_cb)
        except Exception:
            pass
            
    threading.Thread(target=_run, daemon=True).start()
    logger.info(f"Gemini Web Search macro scheduled (Advanced version) for: {query}")

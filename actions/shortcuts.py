import pyautogui
import logging

logger = logging.getLogger("Lucky.Actions.Shortcuts")

def copy():
    pyautogui.hotkey('ctrl', 'c')
    logger.info("Copied")

def paste():
    pyautogui.hotkey('ctrl', 'v')
    logger.info("Pasted")

def undo():
    pyautogui.hotkey('ctrl', 'z')
    logger.info("Undo")

def redo():
    pyautogui.hotkey('ctrl', 'y')
    logger.info("Redo")

def remove():
    pyautogui.press('backspace')
    logger.info("Backspaced / Removed")

def scroll_up():
    pyautogui.scroll(500)
    logger.info("Scrolled Up")

def scroll_down():
    pyautogui.scroll(-500)
    logger.info("Scrolled Down")

def minimize_all():
    pyautogui.hotkey('win', 'd')
    logger.info("Minimized all windows")

def maximize_all():
    pyautogui.hotkey('win', 'shift', 'm')
    logger.info("Maximized all windows")

def close_tab():
    pyautogui.hotkey('ctrl', 'w')
    logger.info("Closed Tab")

def next_tab():
    pyautogui.hotkey('ctrl', 'tab')
    logger.info("Next Tab")

def prev_tab():
    pyautogui.hotkey('ctrl', 'shift', 'tab')
    logger.info("Previous Tab")

def dictate(text: str):
    if not text: return
    # Use clipboard paste for full Unicode support (Hindi, emojis, special chars)
    import pyperclip
    old_clipboard = None
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    import time
    time.sleep(0.1)
    # Restore previous clipboard content
    if old_clipboard is not None:
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass
    logger.info(f"Dictated text: {text}")

def execute_shortcut(intent: str):
    # Route intent to specific macro
    mapping = {
        "COPY": copy,
        "PASTE": paste,
        "UNDO": undo,
        "REDO": redo,
        "MINIMIZE_ALL": minimize_all,
        "MAXIMIZE_ALL": maximize_all,
        "CLOSE_TAB": close_tab,
        "NEXT_TAB": next_tab,
        "PREV_TAB": prev_tab,
        "REMOVE": remove,
        "SCROLL_UP": scroll_up,
        "SCROLL_DOWN": scroll_down
    }
    if intent in mapping:
        mapping[intent]()
        return True
    return False

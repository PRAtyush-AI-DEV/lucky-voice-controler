import os
import subprocess
import logging
import pyautogui
from datetime import datetime

logger = logging.getLogger("Lucky.Actions.Files")

def _preferred_desktop_path() -> str:
    """
    On many Windows setups, Desktop is redirected to OneDrive.
    Prefer OneDrive Desktop if it exists; otherwise fall back to the default.
    """
    user_profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    candidates = [
        os.path.join(user_profile, "OneDrive", "Desktop"),
        os.path.join(user_profile, "Desktop"),
        os.path.expanduser("~/Desktop"),
    ]
    for p in candidates:
        if p and os.path.isdir(p):
            return p
    return candidates[-1]


COMMON_FOLDERS = {
    "downloads": os.path.expanduser("~/Downloads"),
    "desktop": _preferred_desktop_path(),
    "documents": os.path.expanduser("~/Documents"),
    "pictures": os.path.expanduser("~/Pictures"),
    "music": os.path.expanduser("~/Music"),
    "videos": os.path.expanduser("~/Videos")
}

def open_folder(folder_name: str) -> bool:
    if not folder_name: return False
    
    # Special recent files command
    if "recent" in folder_name:
        subprocess.Popen("explorer shell:recent")
        logger.info("Opened recent files")
        return True
        
    for key, path in COMMON_FOLDERS.items():
        if key in folder_name:
            if os.path.exists(path):
                os.startfile(path)
                logger.info(f"Opened folder: {path}")
                return True
                
    logger.warning(f"Folder '{folder_name}' mapped path not found.")
    return False

def create_folder(folder_name: str = "New Folder"):
    # Accept None safely (FIX: NoneType crash)
    folder_name = (folder_name or "New Folder")
    if not isinstance(folder_name, str):
        folder_name = str(folder_name)
        
    # Simplistic creation on Desktop by default
    desktop = _preferred_desktop_path()
    # Clean string if it says 'naya folder banao'
    clean_name = (
        folder_name
        .replace("naya folder banao", "")
        .replace("new folder", "")
        .replace("नया फोल्डर", "")
        .replace("फोल्डर बनाओ", "")
        .strip()
    )
    if not clean_name:
        clean_name = "New Folder"
        
    path = os.path.join(desktop, clean_name)
    try:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Created folder at {path}")
        return True
    except Exception as e:
        logger.error(f"Failed creating folder: {e}")
        return False

def take_screenshot():
    try:
        desktop = _preferred_desktop_path()
        fname = f"Screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(desktop, fname)
        pyautogui.screenshot(path)
        logger.info(f"Screenshot taken: {path}")
        return True
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return False

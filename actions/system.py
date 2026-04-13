"""
actions/system.py — System Controls V2
=======================================
Fixes:
- [#8] lucky.key now protected with Windows DPAPI via win32crypt.
       If an old unprotected key exists, it is automatically migrated.
"""

import os
import time
import ctypes
import json
import logging
import pyautogui

logger = logging.getLogger("Lucky.Actions.System")

KEY_FILE = "lucky.key"
# Sentinel prefix written into the key file so we can detect already-DPAPI-wrapped keys
_DPAPI_MARKER = b"DPAPI:"


# ─────────────────────────────────────────────
# Key management (FIX #8 — DPAPI protection)
# ─────────────────────────────────────────────

def _dpapi_encrypt(data: bytes) -> bytes:
    """Encrypt bytes using Windows DPAPI (current-user scope)."""
    import win32crypt
    encrypted = win32crypt.CryptProtectData(data, "LuckyKey", None, None, None, 0)
    return encrypted


def _dpapi_decrypt(encrypted: bytes) -> bytes:
    """Decrypt bytes using Windows DPAPI."""
    import win32crypt
    _, decrypted = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
    return decrypted


def _migrate_plain_key(raw_key: bytes) -> bytes:
    """
    If the existing key file contains a plain Fernet key (not DPAPI-wrapped),
    wrap it with DPAPI and overwrite the key file.
    Returns the raw Fernet key bytes for immediate use.
    """
    logger.info("Migrating lucky.key → DPAPI-protected format...")
    try:
        encrypted = _dpapi_encrypt(raw_key)
        with open(KEY_FILE, "wb") as f:
            f.write(_DPAPI_MARKER + encrypted)
        logger.info("Key migration complete.")
    except Exception as e:
        logger.error(f"DPAPI migration failed (pywin32 installed?): {e}")
        logger.warning("Falling back to plain key storage.")
    return raw_key


def _get_or_create_key() -> bytes:
    """
    Return the raw Fernet key, creating and DPAPI-protecting it if needed.
    Handles migration from old plain-text key files automatically.
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            content = f.read()

        if content.startswith(_DPAPI_MARKER):
            # Already DPAPI-wrapped — decrypt and return
            try:
                raw_key = _dpapi_decrypt(content[len(_DPAPI_MARKER):])
                return raw_key
            except Exception as e:
                logger.error(f"Failed to DPAPI-decrypt key: {e}")
                # Last resort: regenerate (password will need reset)
                return _create_new_key()
        else:
            # Old plain-text key — migrate it
            return _migrate_plain_key(content)
    else:
        return _create_new_key()


def _create_new_key() -> bytes:
    """Generate a new Fernet key and store it DPAPI-protected."""
    from cryptography.fernet import Fernet
    raw_key = Fernet.generate_key()
    try:
        encrypted = _dpapi_encrypt(raw_key)
        with open(KEY_FILE, "wb") as f:
            f.write(_DPAPI_MARKER + encrypted)
        logger.info("New DPAPI-protected key created.")
    except Exception as e:
        logger.error(f"DPAPI unavailable, storing plain key: {e}")
        with open(KEY_FILE, "wb") as f:
            f.write(raw_key)
    return raw_key


# ─────────────────────────────────────────────
# Password management
# ─────────────────────────────────────────────

def setup_password(config: dict):
    """First-time wizard to setup lock password."""
    if config.get("lock_password_hash"):
        return  # Already setup

    print("\n--- [ LUCKY PASSWORD SETUP ] ---")
    print("Welcome! Set your Windows password so Lucky can unlock for you.")
    import getpass
    pwd = getpass.getpass("Enter Windows Password: ")

    from cryptography.fernet import Fernet
    key = _get_or_create_key()
    f   = Fernet(key)
    encrypted = f.encrypt(pwd.encode()).decode()

    config["lock_password_hash"] = encrypted
    with open("config.json", "w", encoding="utf-8") as f_out:
        json.dump(config, f_out, indent=2, ensure_ascii=False)

    print("Password securely encrypted and saved!\n")
    logger.info("Password setup completed.")


def get_password(config: dict) -> str:
    from cryptography.fernet import Fernet
    key       = _get_or_create_key()
    f         = Fernet(key)
    encrypted = config.get("lock_password_hash", "")
    if not encrypted:
        return ""
    try:
        return f.decrypt(encrypted.encode()).decode()
    except Exception as e:
        logger.error(f"Failed to decrypt password: {e}")
        return ""


# ─────────────────────────────────────────────
# System actions
# ─────────────────────────────────────────────

def lock_screen():
    logger.info("Locking screen...")
    ctypes.windll.user32.LockWorkStation()


def unlock_screen(config: dict):
    logger.info("Attempting to unlock screen...")
    pwd = get_password(config)
    if not pwd:
        logger.warning("No password setup. Cannot unlock.")
        return

    # Wake screen
    pyautogui.press("space")
    time.sleep(0.5)

    # Type password using clipboard for Unicode/special char support
    import pyperclip
    old_clipboard = None
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass
    pyperclip.copy(pwd)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.1)
    # Clear password from clipboard immediately
    pyperclip.copy("")
    if old_clipboard is not None:
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass
    pyautogui.press("enter")


def sleep_system():
    logger.info("Scheduling Sleep mode...")
    import subprocess
    subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)


def shutdown():
    logger.info("Scheduling shutdown in 10 seconds...")
    os.system("shutdown /s /t 10")


def restart():
    logger.info("Scheduling restart in 10 seconds...")
    os.system("shutdown /r /t 10")

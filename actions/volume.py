import logging
import screen_brightness_control as sbc
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

logger = logging.getLogger("Lucky.Actions.Volume")

def _get_volume_interface():
    # Helper to get the pycaw audio interface
    try:
        import pythoncom
        pythoncom.CoInitialize()  # Required when called from daemon threads
        devices = AudioUtilities.GetSpeakers()
        if not devices: return None
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        logger.error(f"Could not get audio endpoint: {e}")
        return None

def set_volume(percent: int):
    # Ensure percent is between 0 and 100
    percent = max(0, min(100, percent))
    vol = _get_volume_interface()
    if vol:
        # volume goes from 0.0 to 1.0 (scalar)
        vol.SetMasterVolumeLevelScalar(percent / 100.0, None)
        logger.info(f"Volume set to {percent}%")
        
def get_volume() -> int:
    vol = _get_volume_interface()
    if vol:
        return int(vol.GetMasterVolumeLevelScalar() * 100.0)
    return 0

def volume_up(amount: int = 50):
    current = get_volume()
    set_volume(current + amount)

def volume_down(amount: int = 50):
    current = get_volume()
    set_volume(current - amount)

def mute():
    vol = _get_volume_interface()
    if vol:
        vol.SetMute(1, None)
        logger.info("Volume muted.")

def unmute():
    vol = _get_volume_interface()
    if vol:
        vol.SetMute(0, None)
        logger.info("Volume unmuted.")

# --- BRIGHTNESS ---
def set_brightness(percent: int):
    try:
        sbc.set_brightness(percent)
        logger.info(f"Brightness set to {percent}%")
    except Exception as e:
        logger.error(f"Brightness Error: {e}")
        
def get_brightness() -> int:
    try:
        b = sbc.get_brightness()
        return b[0] if isinstance(b, list) else b
    except Exception:
        return 50

def brightness_up(amount: int = 50):
    current = get_brightness()
    set_brightness(current + amount)
    
def brightness_down(amount: int = 50):
    current = get_brightness()
    set_brightness(current - amount)

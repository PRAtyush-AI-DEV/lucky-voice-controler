import subprocess
import logging

logger = logging.getLogger("Lucky.Actions.WiFi_BT")

def _is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def toggle_wifi(enable: bool):
    action = "enable" if enable else "disable"
    if not _is_admin():
        logger.error("WiFi toggle requires Admin privileges.")
        return False
    try:
        # Note: netsh interface set often requires administrative privileges
        subprocess.run(["netsh", "interface", "set", "interface", "Wi-Fi", action], check=True)
        logger.info(f"WiFi {action}d successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to toggle WiFi (might need Admin privileges): {e}")
        return False

def toggle_bluetooth(enable: bool):
    action = "Enable-PnpDevice" if enable else "Disable-PnpDevice"
    # PowerShell command to toggle Bluetooth radios. Also normally requires admin
    ps_command = f"Get-PnpDevice -Class Bluetooth | {action} -Confirm:$false"
    if not _is_admin():
        logger.error("Bluetooth toggle requires Admin privileges. Please run Lucky as Administrator.")
        return False
    try:
        subprocess.run(["powershell", "-Command", ps_command], check=True)
        logger.info(f"Bluetooth toggled (enable={enable}) successfully.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to toggle Bluetooth (requires Admin): {e}")
        return False

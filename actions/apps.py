import os
import subprocess
import shutil
import psutil
import time
import logging

logger = logging.getLogger("Lucky.Actions.Apps")

def open_app(entity: str, config: dict):
    if not entity: return False
    
    aliases = config.get("app_aliases", {})
    # Match alias
    for alias, path in aliases.items():
        if alias in entity:
            logger.info(f"Opening mapped app/folder: {alias} -> {path}")
            try:
                if path.startswith("code ") or path.startswith("cmd "):
                    import subprocess
                    subprocess.Popen(path, shell=True)
                else:
                    os.startfile(path)
                return True
            except Exception as e:
                logger.error(f"Failed to open '{path}': {e}")
                return False
                
    # If not in aliases, try windows PATH
    executable = f"{entity}.exe"
    path = shutil.which(executable)
    if path:
        logger.info(f"Opening discovered app: {path}")
        subprocess.Popen(path)
        return True
        
    logger.warning(f"Could not find app associated with '{entity}'")
    return False

def close_app(entity: str):
    if not entity: return False
    
    found = False
    for proc in psutil.process_iter(['name']):
        try:
            # Fuzzy process matcher
            if entity.lower() in proc.info['name'].lower():
                logger.info(f"Terminating process: {proc.info['name']} (PID: {proc.pid})")
                proc.terminate()
                found = True
                
                # Graceful wait
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    logger.warning(f"{proc.info['name']} did not close in time, forcing kill...")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
            
    return found

def get_running_apps():
    # Only return unique apps with GUIs typically, but for simplicity we list non-system processes
    apps = set()
    system_procs = {"system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe", "svchost.exe"}
    
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name.lower() not in system_procs and not name.startswith("System"):
                apps.add(name)
        except Exception:
            pass
    return list(apps)

import keyboard
import logging

logger = logging.getLogger("Lucky.Actions.Media")

def play_pause():
    logger.info("Media: Play/Pause")
    keyboard.send("play/pause media")

def next_track():
    logger.info("Media: Next Track")
    keyboard.send("next track")

def prev_track():
    logger.info("Media: Previous Track")
    keyboard.send("previous track")


"""
audio_utils.py — Shared audio helper functions
================================================
Extracted from speech_to_text.py and wake_word.py to avoid duplication.
"""

import struct
import math

SAMPLE_WIDTH = 2  # 16-bit audio = 2 bytes per sample


def rms(data: bytes) -> float:
    """Calculate Root Mean Square (energy level) of raw audio bytes."""
    if len(data) < 2:
        return 0.0
    count = len(data) // SAMPLE_WIDTH
    shorts = struct.unpack(f"{count}h", data[:count * SAMPLE_WIDTH])
    sum_sq = sum(s * s for s in shorts)
    return math.sqrt(sum_sq / count) if count else 0.0

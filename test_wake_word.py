"""
test_wake_word.py — Wake Word Detection Test
=============================================
Chalao aur microphone mein "Lucky" bolo.
Ctrl+C se band karo.

Modes:
  - Agar Porcupine config sahi hai → Porcupine engine use hoga
  - Warna → SpeechRecognition fallback use hoga
"""

import json
import time
import logging

# Sirf errors dikhao (spinner disturb na ho)
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def load_config():
    with open("config.json", "r") as f:
        return json.load(f)


def on_wake_word():
    """Callback — Lucky detect hone par call hoga."""
    print("\n" + "=" * 55)
    print("   *** LUCKY DETECT HUA! CALLBACK TRIGGERED! ***")
    print("=" * 55)
    print("   Ab command sun-ne ka kaam yahan hoga (Step 4)")
    print("=" * 55 + "\n")


def main():
    from wake_word import WakeWordDetector

    config = load_config()

    print("\n" + "=" * 55)
    print("   Lucky Voice Controller — Wake Word Test")
    print("=" * 55)
    print("   Microphone mein clearly 'Lucky' bolo")
    print("   Band karne ke liye: Ctrl+C dabao")
    print("=" * 55)

    detector = WakeWordDetector(config=config, callback=on_wake_word)
    print(f"\n  Active Engine: [{detector.engine_type.upper()}]\n")

    detector.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\n  [Test] Band ho raha hoon...")
        detector.stop()
        time.sleep(0.5)
        print("  [Test] Done! Goodbye.")


if __name__ == "__main__":
    main()

import sys
import os
import io

# Force UTF-8 for Devanagari print debugging
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intent_parser import IntentParser

config = {
    "app_aliases": {
        "recycle bin": "shell:RecycleBinFolder"
    }
}

parser = IntentParser(config)

test_cases = [
    "जेमिनी बोलो",
    "जेमिनी पर सर्च करो मौसम",
    "रिसाइकिलिंग होना",
    "रिसाइकिल बिन हो",
    "gemini search weather"
]

print("=== VERIFICATION RESULTS ===")
for text in test_cases:
    # Standardize devanagari errors beforehand (using private method for testing)
    from intent_parser import _map_devanagari_to_english
    mapped = _map_devanagari_to_english(text.lower().strip())
    res = parser.parse(text)
    print(f"Text: '{text}'")
    print(f"  Mapped: '{mapped}'")
    print(f"  Intent: {res['intent']}, Entity: {res['entity']}, Conf: {res.get('confidence')}")

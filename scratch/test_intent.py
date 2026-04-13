import sys
import os
import json
from intent_parser import IntentParser

# Load config
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

parser = IntentParser(config)

tests = [
    "यह फोल्डर बनाओ",
    "कहने लगा",
    "करण औजला का गाना लगाओ",
    "बोलो",
    "क्रोम खुला",
    "हनी सिंह का गाना लगा",
    "हनी सिंह का गाना",
    "वॉक करो",
    "सिद्धू मूस वाला बताने लगा"
]

for t in tests:
    res = parser.parse(t)
    print(f"'{t}' -> {res['intent']} | entity={res['entity']}")

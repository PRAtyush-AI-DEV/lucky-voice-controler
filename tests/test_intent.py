import unittest
from intent_parser import IntentParser

class TestIntentParserV2(unittest.TestCase):
    def setUp(self):
        self.config = {}
        self.parser = IntentParser(self.config)

    def test_known_intents(self):
        cases = {
            "lucky unlock karo": "UNLOCK_SCREEN",
            "laptop lock karo": "LOCK_SCREEN",
            "chrome kholo": "OPEN_APP", # entity chrome
            "youtube kholo": "OPEN_WEBSITE", # entity youtube
            "gmail kholo": "OPEN_WEBSITE", # entity gmail
            "downloads kholo": "OPEN_FOLDER", # entity downloads
            "volume badha do": "VOLUME_UP",
            "screenshot le": "SCREENSHOT",
            "wifi on karo": "WIFI_ON",
            "bluetooth band karo": "BLUETOOTH_OFF",
            "copy karo": "COPY",
            "sab minimize karo": "MINIMIZE_ALL",
            "spotify band karo": "CLOSE_APP",
            "brightness kam karo": "BRIGHTNESS_DOWN",
            "computer shutdown karo": "SHUTDOWN",
            "laptop sulao": "SLEEP"
        }
        
        for phrase, expected_intent in cases.items():
            # Remove "lucky" if present as the wake word isn't part of intent
            phrase = phrase.replace("lucky ", "")
            result = self.parser.parse(phrase)
            self.assertEqual(result["intent"], expected_intent, f"Failed on '{phrase}', got {result['intent']}")

    def test_advanced_entity_extraction(self):
        # Timer
        r1 = self.parser.parse("25 minute ka timer laga")
        self.assertEqual(r1["intent"], "TIMER")
        self.assertEqual(r1["entity"], 25)
        
        # Alarm
        r2 = self.parser.parse("5 baje alarm laga")
        self.assertEqual(r2["intent"], "ALARM")
        self.assertEqual(r2["entity"]["time"], "5")

        # Dictation
        r3 = self.parser.parse("yeh likh: meeting kal 5 baje hai")
        self.assertEqual(r3["intent"], "DICTATE")
        self.assertEqual(r3["entity"], "meeting kal 5 baje hai")

if __name__ == '__main__':
    unittest.main()

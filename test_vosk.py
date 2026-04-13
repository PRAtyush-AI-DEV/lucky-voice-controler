import os
import unittest


class TestVoskAndPyAudio(unittest.TestCase):
    def test_vosk_model_load(self):
        # Match the repo README defaults
        model_path = os.path.join("models", "vosk-model-small-en-us-0.15")
        if not os.path.isdir(model_path):
            self.skipTest(
                f"Vosk model not found at '{model_path}'. Download models into the 'models/' folder."
            )

        from vosk import Model, KaldiRecognizer

        m = Model(model_path)
        _ = KaldiRecognizer(m, 16000)

    def test_pyaudio_microphone_detection(self):
        import pyaudio

        pa = pyaudio.PyAudio()
        try:
            count = pa.get_device_count()
            self.assertGreaterEqual(count, 0)
        finally:
            pa.terminate()


if __name__ == "__main__":
    unittest.main(verbosity=2)

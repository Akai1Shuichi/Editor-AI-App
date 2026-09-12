import unittest

from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from app import config
from app.ui.tts_tab import TTSTab
from app.ui.voice_lookup_tab import VoiceLookupTab


class SlowWorker(QThread):
    def run(self):
        self.msleep(250)


class VoiceLookupThreadLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_opening_lookup_from_tts_starts_only_one_load(self):
        tab = TTSTab()
        original_key = config.VIBI_API_KEY
        config.VIBI_API_KEY = "diagnostic-key"
        load_calls = []
        tab.voice_lookup_tab.load_voices = lambda: load_calls.append("load")
        try:
            tab.open_voice_lookup()
        finally:
            config.VIBI_API_KEY = original_key

        self.assertEqual(load_calls, ["load"])

    def test_running_voice_worker_is_not_replaced(self):
        tab = VoiceLookupTab()
        existing_worker = SlowWorker()
        tab.worker = existing_worker
        existing_worker.start()

        original_key = config.VIBI_API_KEY
        config.VIBI_API_KEY = ""
        try:
            tab.load_voices()
            replacement_worker = tab.worker
            if replacement_worker is not existing_worker:
                replacement_worker.wait(1000)
            existing_worker.wait(1000)
        finally:
            config.VIBI_API_KEY = original_key

        self.assertIs(tab.worker, existing_worker)


if __name__ == "__main__":
    unittest.main()

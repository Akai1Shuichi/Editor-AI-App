import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSettings

from app.core.standalone_state import (
    StandaloneStateStore,
    build_output_folder_name,
    resolve_new_output_folder,
)


class StandaloneStateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings_path = Path(self.temp_dir.name) / "settings.ini"
        self.settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
        self.store = StandaloneStateStore(self.settings)

    def tearDown(self):
        self.settings.clear()
        self.settings.sync()
        self.temp_dir.cleanup()

    def test_watermark_state_restores_only_existing_files(self):
        existing = Path(self.temp_dir.name) / "source.png"
        missing = Path(self.temp_dir.name) / "missing.png"
        output_dir = Path(self.temp_dir.name) / "watermark-output"
        existing.write_bytes(b"image")
        output_dir.mkdir()

        self.store.save_watermark([existing, missing], output_dir)

        state = self.store.load_watermark()
        self.assertEqual(state["files"], [existing])
        self.assertEqual(state["output_dir"], output_dir)

    def test_tts_state_round_trips_and_ignores_missing_results(self):
        audio = Path(self.temp_dir.name) / "voice.mp3"
        missing_srt = Path(self.temp_dir.name) / "voice.srt"
        audio.write_bytes(b"audio")
        original = {
            "script": "Xin chào",
            "provider": "minimax",
            "voice_id": "voice-123",
            "model": "speech-2.8-hd",
            "language": "Vietnamese",
            "stability": -2,
            "similarity": 110,
            "speed": 95,
            "export_srt": True,
            "subtab": 1,
            "audio_path": str(audio),
            "srt_path": str(missing_srt),
        }

        self.store.save_tts(original)

        state = self.store.load_tts()
        self.assertEqual(state["script"], "Xin chào")
        self.assertEqual(state["provider"], "minimax")
        self.assertEqual(state["stability"], -2)
        self.assertEqual(state["audio_path"], audio)
        self.assertIsNone(state["srt_path"])

    def test_last_page_is_limited_to_known_sidebar_pages(self):
        self.store.save_last_page(2)
        self.assertEqual(self.store.load_last_page(), 2)

        self.store.save_last_page(99)
        self.assertEqual(self.store.load_last_page(), 0)

    def test_output_folder_names_use_the_requested_timestamp_order(self):
        instant = datetime(2026, 9, 11, 14, 5, 7)

        self.assertEqual(
            build_output_folder_name("clean", instant, day_first=False),
            "clean_20260911_140507",
        )
        self.assertEqual(
            build_output_folder_name("voice", instant, day_first=True),
            "voice_11092026_140507",
        )

    def test_new_output_folder_rejects_duplicates_and_nested_names(self):
        root = Path(self.temp_dir.name) / "downloads"
        root.mkdir()

        self.assertEqual(
            resolve_new_output_folder(root, "voice_demo"),
            root / "voice_demo",
        )
        (root / "voice_demo").mkdir()
        with self.assertRaises(FileExistsError):
            resolve_new_output_folder(root, "voice_demo")
        with self.assertRaises(ValueError):
            resolve_new_output_folder(root, "nested/name")
        with self.assertRaises(ValueError):
            resolve_new_output_folder(root, "voice:demo")
        with self.assertRaises(ValueError):
            resolve_new_output_folder(root, "CON")


if __name__ == "__main__":
    unittest.main()

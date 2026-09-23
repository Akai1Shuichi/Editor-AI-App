import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication

from app import config
from app.ui.video_watermark_tab import VideoWatermarkTab
from app.ui.main_window import MainWindow


class VideoWatermarkUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_tab_accepts_supported_video_formats(self):
        """Catches a chooser that rejects one of the documented video formats."""
        tab = VideoWatermarkTab()

        for extension in ("*.mp4", "*.mov", "*.mkv", "*.webm"):
            self.assertIn(extension, tab.video_filter)
        self.assertEqual(
            {tab.mode_choice.itemData(index) for index in range(tab.mode_choice.count())},
            {"veo3", "gemini"},
        )
        tab.close()

    def test_video_watermark_mode_is_restored_from_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(
                str(Path(directory) / "settings.ini"), QSettings.Format.IniFormat
            )
            with patch.object(config, "SETTINGS", settings), patch.object(
                config, "reload_config"
            ):
                first_tab = VideoWatermarkTab()
                self.assertEqual(first_tab.mode_choice.currentData(), "veo3")
                first_tab.mode_choice.setCurrentIndex(
                    first_tab.mode_choice.findData("gemini")
                )
                first_tab.close()

                restored_tab = VideoWatermarkTab()
                self.assertEqual(restored_tab.mode_choice.currentData(), "gemini")
                restored_tab.close()

    def test_main_window_exposes_separate_video_watermark_page(self):
        """Catches video removal being implemented but unreachable from the app."""
        window = MainWindow()

        labels = [window.watermark_pages.tabText(index) for index in range(window.watermark_pages.count())]

        self.assertIn("Gỡ watermark Video", labels)
        window.close()


if __name__ == "__main__":
    unittest.main()

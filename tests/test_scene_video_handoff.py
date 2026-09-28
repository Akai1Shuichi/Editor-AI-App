import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from app.ui.scene_tab import SceneTab
from app.ui.video_tab import VideoTab


class SceneVideoHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_pasted_scene_json_builds_timeline_without_saving_a_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "SC01.png"
            audio = root / "voice.mp3"
            srt = root / "voice.srt"
            image.write_bytes(b"image")
            audio.write_bytes(b"audio")
            srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello\n", encoding="utf-8")

            scene = SceneTab()
            video = VideoTab()
            scene.scene_path_changed.connect(video.set_json_file)
            try:
                video.txt_image_dir.setText(str(root))
                video.txt_audio_file.setText(str(audio))
                video.txt_srt_file.setText(str(srt))
                scene.txt_scene_content.setPlainText(json.dumps([
                    {"id": "SC01", "subtitle_ids": [1]}
                ]))

                with patch("app.ui.video_tab.video_creator.get_ffmpeg_path", return_value="ffmpeg"), \
                     patch("app.ui.video_tab.video_creator.get_audio_duration", return_value=2.0):
                    self.assertTrue(video.analyze_timeline())
                self.assertEqual(video.current_timeline[0]["id"], "SC01")
                self.assertEqual(video.current_timeline[0]["image"], image)
                self.assertEqual(video.txt_json_file.text(), "")
            finally:
                scene.close()
                video.close()

    def test_editing_text_replaces_old_file_and_invalid_input_clears_timeline(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "scenes.json"
            source.write_text('[{"id": "OLD"}]', encoding="utf-8")
            (root / "NEW.png").write_bytes(b"image")
            audio = root / "voice.mp3"
            srt = root / "voice.srt"
            audio.write_bytes(b"audio")
            srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHello\n", encoding="utf-8")
            scene = SceneTab()
            video = VideoTab()
            scene.scene_path_changed.connect(video.set_json_file)
            try:
                video.txt_image_dir.setText(str(root))
                video.txt_audio_file.setText(str(audio))
                video.txt_srt_file.setText(str(srt))
                scene.combo_mode.setCurrentIndex(1)
                scene.txt_scene_path.setText(str(source))
                self.assertEqual(video.txt_json_file.text(), str(source))

                scene.combo_mode.setCurrentIndex(0)
                scene.txt_scene_content.setPlainText('[{"id": "NEW"}]')
                self.assertEqual(video.txt_json_file.text(), "")
                self.assertEqual(source.read_text(encoding="utf-8"), '[{"id": "OLD"}]')
                with patch("app.ui.video_tab.video_creator.get_ffmpeg_path", return_value="ffmpeg"), \
                     patch("app.ui.video_tab.video_creator.get_audio_duration", return_value=2.0):
                    self.assertTrue(video.analyze_timeline())
                self.assertEqual(video.current_timeline[0]["id"], "NEW")

                scene.txt_scene_content.setPlainText("not JSON")
                self.assertEqual(video.current_timeline, [])
                self.assertFalse(video.analyze_timeline())
            finally:
                scene.close()
                video.close()


if __name__ == "__main__":
    unittest.main()

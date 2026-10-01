import json
import os
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.core import edit_document
from app.core.project_manager import Project
from app.ui.video_tab import VideoTab


def make_project(root):
    project = Project(root)
    (project.clean_images_dir / "SC01.png").write_bytes(b"image")
    (project.clean_images_dir / "SC02.png").write_bytes(b"image")
    (project.voice_dir / "voice.mp3").write_bytes(b"audio")
    (project.voice_dir / "voice.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nXin chào\n\n"
        "2\n00:00:02,000 --> 00:00:04,000\nTạm biệt\n", encoding="utf-8",
    )
    return project


def make_document(project):
    return edit_document.create_document(
        project.path,
        [{"index": i, "id": f"SC{i:02d}", "subtitles": [i],
          "image": project.clean_images_dir / f"SC{i:02d}.png",
          "start": (i - 1) * 2, "end": i * 2} for i in (1, 2)],
        {1: {"start": 0, "end": 2, "text": "Xin chào"},
         2: {"start": 2, "end": 4, "text": "Tạm biệt"}},
        project.clean_images_dir, project.voice_dir / "voice.mp3",
        project.voice_dir / "voice.srt", "16:9", 30, 4,
    )


class EditDocumentStorageTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.project = make_project(self.root / "original")
        self.document = make_document(self.project)

    def test_edits_survive_round_trip_and_project_move(self):
        document = self.document
        document["tracks"]["video"][0]["end"] = 1.5
        document["tracks"]["video"][1]["start"] = 1.5
        document["tracks"]["subtitles"][0]["text"] = "Chữ đã chỉnh sửa"
        document["settings"] = {"aspect_ratio": "9:16", "fps": 60}
        document["view_state"] = {"playhead": 1.25}
        external = self.root / "external.png"
        external.write_bytes(b"external")
        document["tracks"]["video"][1]["media"] = edit_document.media_reference(self.project.path, external)
        self.project.save_edit_document(document)
        moved = self.root / "moved"
        self.project.path.rename(moved)
        project = Project(moved)
        loaded = project.load_edit_document()
        self.assertEqual(loaded, document)
        timeline = edit_document.document_timeline(moved, loaded)
        self.assertEqual([clip["duration"] for clip in timeline], [1.5, 2.5])
        self.assertEqual(timeline[0]["image"], moved / "images/clean/SC01.png")
        self.assertEqual(timeline[1]["image"], external)
        # Missing media is recoverable and must not erase its saved reference.
        timeline[0]["image"].unlink()
        self.assertEqual(project.load_edit_document(), document)

    def test_import_cannot_overwrite_and_explicit_rebuild_keeps_backup(self):
        self.project.save_edit_document(self.document)
        previous = self.project.edit_path.read_bytes()
        updated = deepcopy(self.document)
        updated["tracks"]["subtitles"][0]["text"] = "Bản mới"
        with self.assertRaises(FileExistsError):
            self.project.save_edit_document(updated)
        self.assertEqual(self.project.edit_path.read_bytes(), previous)
        self.project.save_edit_document(updated, overwrite=True, backup=True)
        self.assertEqual(self.project.load_edit_document(), updated)
        self.assertEqual(self.project.edit_path.with_suffix(".json.bak").read_bytes(), previous)

    def test_failed_atomic_replace_keeps_original_and_removes_temporary_file(self):
        self.project.save_edit_document(self.document)
        previous = self.project.edit_path.read_bytes()
        with patch("app.core.edit_document.os.replace", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.project.save_edit_document(self.document, overwrite=True)
        self.assertEqual(self.project.edit_path.read_bytes(), previous)
        self.assertEqual(list(self.project.path.glob(".edit-*.tmp")), [])

    def test_invalid_or_newer_documents_are_rejected_without_modifying_files(self):
        cases = []
        for field, value in (("version", 99), ("duration", float("nan")), ("tracks", [])):
            bad = deepcopy(self.document)
            bad[field] = value
            cases.append(bad)
        bad = deepcopy(self.document)
        bad["tracks"]["video"][1]["id"] = bad["tracks"]["video"][0]["id"]
        cases.append(bad)
        bad = deepcopy(self.document)
        bad["tracks"]["video"][0]["end"] = -1
        cases.append(bad)
        for document in cases:
            with self.subTest(document=document):
                payload = json.dumps(document).encode()
                self.project.edit_path.write_bytes(payload)
                with self.assertRaises(ValueError):
                    self.project.load_edit_document()
                with self.assertRaises(ValueError):
                    self.project.save_edit_document(document, overwrite=True)
                self.assertEqual(self.project.edit_path.read_bytes(), payload)


class EditDocumentUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.project = make_project(self.root / "project")
        self.video = VideoTab()
        self.addCleanup(self.video.close)
        self.video.set_project(self.project)
        self.video.set_json_file([{"id": "SC01", "subtitles": [1]},
                                  {"id": "SC02", "subtitles": [2]}])
        for target, value in (("get_ffmpeg_path", "ffmpeg"), ("get_audio_duration", 4.0)):
            mock = patch(f"app.ui.video_tab.video_creator.{target}", return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def create_draft(self):
        self.assertTrue(self.video.analyze_timeline())
        self.assertTrue(self.project.edit_path.exists())

    def test_open_and_analyze_keep_saved_edits_when_sources_change(self):
        self.create_draft()
        document = self.project.load_edit_document()
        document["tracks"]["video"][0]["end"] = 1.5
        document["tracks"]["video"][1]["start"] = 1.5
        document["tracks"]["subtitles"][0]["text"] = "Đã sửa"
        self.project.save_edit_document(document, overwrite=True)
        previous = self.project.edit_path.read_bytes()
        newer_voice = self.project.voice_dir / "newer.mp3"
        newer_voice.write_bytes(b"newer audio")
        (self.project.voice_dir / "voice.srt").unlink()
        self.video.set_project(self.project)
        self.assertEqual(self.video.current_timeline[0]["duration"], 1.5)
        self.assertEqual(Path(self.video.txt_audio_file.text()).name, "voice.mp3")
        self.video.set_json_file(None)
        self.video.set_audio_and_srt(str(newer_voice), "")
        self.video.auto_detect_defaults()
        with patch("app.ui.video_tab.video_creator.compute_timeline") as compute:
            self.assertTrue(self.video.analyze_timeline())
            compute.assert_not_called()
        self.assertEqual(self.video.edit_document, document)
        self.assertEqual(self.project.edit_path.read_bytes(), previous)
        with patch("app.ui.video_tab.VideoRenderWorker") as worker:
            self.video.start_render()
            self.assertEqual(worker.call_args.kwargs["audio_path"], self.project.voice_dir / "voice.mp3")
            self.assertEqual(worker.call_args.kwargs["timeline"][0]["duration"], 1.5)
            self.video.worker = None

    def test_rebuild_requires_confirmation_and_backs_up_previous_draft(self):
        self.create_draft()
        previous = self.project.edit_path.read_bytes()
        self.video.set_json_file([{"id": "SC02", "subtitles": [1, 2]}])
        with patch("app.ui.video_tab.QMessageBox.question", return_value=QMessageBox.StandardButton.No):
            self.video.rebuild_timeline()
        self.assertEqual(self.project.edit_path.read_bytes(), previous)
        with patch("app.ui.video_tab.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.video.rebuild_timeline()
        self.assertEqual([clip["id"] for clip in self.video.current_timeline], ["SC02"])
        self.assertEqual(self.project.edit_path.with_suffix(".json.bak").read_bytes(), previous)

    def test_failed_rebuild_preserves_saved_and_loaded_draft(self):
        self.create_draft()
        previous = self.project.edit_path.read_bytes()
        document = deepcopy(self.video.edit_document)
        with patch("app.ui.video_tab.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes), \
             patch("app.ui.video_tab.video_creator.compute_timeline", side_effect=ValueError("invalid scenes")), \
             patch("app.ui.video_tab.QMessageBox.warning"):
            self.video.rebuild_timeline()
        self.assertEqual(self.video.edit_document, document)
        self.assertEqual(self.project.edit_path.read_bytes(), previous)

    def test_corrupt_draft_is_not_silently_replaced(self):
        self.project.edit_path.write_text('{"version": 100}', encoding="utf-8")
        previous = self.project.edit_path.read_bytes()
        self.video.set_project(self.project)
        self.assertFalse(self.video.analyze_timeline())
        self.assertEqual(self.video.current_timeline, [])
        self.assertEqual(self.project.edit_path.read_bytes(), previous)

    def test_settings_follow_manual_save_and_auto_save(self):
        self.create_draft()
        self.video.combo_fps.setCurrentIndex(self.video.combo_fps.findData(60))
        self.assertEqual(self.project.load_edit_document()["settings"]["fps"], 30)
        self.assertTrue(self.video.save_current_state())
        self.assertEqual(self.project.load_edit_document()["settings"]["fps"], 60)
        self.video.set_auto_save(True)
        self.video.combo_ratio.setCurrentIndex(self.video.combo_ratio.findData("9:16"))
        self.assertEqual(self.project.load_edit_document()["settings"]["aspect_ratio"], "9:16")
        self.video.set_project(self.project)
        self.assertEqual(self.video.combo_fps.currentData(), 60)
        self.assertEqual(self.video.combo_ratio.currentData(), "9:16")
        another = make_project(self.root / "another")
        self.video.set_project(another)
        self.assertIsNone(self.video.edit_document)
        self.assertEqual(self.video.current_timeline, [])
        self.assertEqual(self.video.total_audio_duration, 0)


if __name__ == "__main__":
    unittest.main()

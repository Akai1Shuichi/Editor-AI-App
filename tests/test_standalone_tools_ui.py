import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QApplication, QLabel, QTabWidget

from app.core.standalone_state import StandaloneStateStore
from app.core.project_manager import Project
from app.ui.project_workspace import ProjectWorkspace
from app.ui.tts_tab import TTSTab
from app.ui.watermark_tab import WatermarkTab


class _SilentMediaPlayer(QObject):
    positionChanged = pyqtSignal(int)
    durationChanged = pyqtSignal(int)
    playbackStateChanged = pyqtSignal(object)

    def setAudioOutput(self, _output):
        pass

    def setSource(self, _source):
        pass


class _SilentAudioOutput:
    def setVolume(self, _volume):
        pass


class _IdleTTSWorker(QObject):
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    task_finished = pyqtSignal(bool, str, str, str)
    last_instance = None

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs
        self.started = False
        _IdleTTSWorker.last_instance = self

    def start(self):
        self.started = True

    def isRunning(self):
        return self.started

    def cancel(self):
        self.started = False


class _IdleWatermarkWorker(QObject):
    file_processed = pyqtSignal(int, int, str, bool, str)
    finished_all = pyqtSignal(int, int)

    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    def start(self):
        pass


class StandaloneToolsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        settings = QSettings(
            str(Path(self.temp_dir.name) / "settings.ini"),
            QSettings.Format.IniFormat,
        )
        self.store = StandaloneStateStore(settings)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_watermark_sidebar_mode_restores_files_and_uses_own_output(self):
        source = Path(self.temp_dir.name) / "flow.png"
        output_dir = Path(self.temp_dir.name) / "watermark"
        source.write_bytes(b"not-a-real-image")
        output_dir.mkdir()
        self.store.save_watermark([source], output_dir)

        tab = WatermarkTab()
        tab.configure_standalone(self.store, output_dir)

        self.assertIsNone(tab.project)
        self.assertEqual(tab.tool_title.text(), "Gỡ watermark Google Flow")
        self.assertEqual(tab.selected_files, [source])
        self.assertEqual(tab.output_dir, output_dir)
        self.assertEqual(tab.table.rowCount(), 1)
        header_texts = [label.text() for label in tab.tool_header.findChildren(QLabel)]
        self.assertNotIn(
            "Làm sạch ảnh hàng loạt; mỗi lượt được lưu trong một thư mục riêng.",
            header_texts,
        )
        self.assertFalse(any(text.startswith("Tự động lưu") for text in header_texts))
        self.assertTrue(tab.chk_custom_out.isHidden())
        self.assertTrue(tab.btn_custom_out.isEnabled())
        self.assertRegex(tab.edit_output_name.text(), r"^clean_\d{8}_\d{6}$")
        self.assertEqual(tab.lbl_output_path.text(), str(output_dir))
        self.assertLessEqual(tab.tool_header.maximumHeight(), 72)

    def test_project_workspace_uses_compact_header_and_tab_status(self):
        project_path = Path(self.temp_dir.name) / "compact-project"
        project = Project(
            project_path,
            {
                "name": "Nguoi que 2D",
                "aspect_ratio": "16:9",
                "fps": 30,
                "created_at": "2026-09-11T20:00:00",
                "updated_at": "2026-09-11T21:17:00",
            },
        )
        for index in range(9):
            (project.clean_images_dir / f"scene-{index}.png").write_bytes(b"image")

        with patch("app.ui.tts_tab.QMediaPlayer", _SilentMediaPlayer), patch(
            "app.ui.tts_tab.QAudioOutput", _SilentAudioOutput
        ), patch(
            "app.ui.voice_lookup_tab.QMediaPlayer", _SilentMediaPlayer
        ), patch(
            "app.ui.voice_lookup_tab.QAudioOutput", _SilentAudioOutput
        ):
            workspace = ProjectWorkspace()
            workspace.set_project(project)

            self.assertEqual(
                workspace.lbl_updated.text(),
                "16:9 · 30 FPS · Đã lưu 11/09/2026 lúc 21:17",
            )
            self.assertEqual(workspace.inner_tabs.tabText(0), "1  Ảnh (9) ✓")
            workspace.action_auto_save.setChecked(True)
            self.assertTrue(workspace.tts_tab.auto_save)

    def test_watermark_preview_switches_from_before_to_after_when_result_arrives(self):
        source = Path(self.temp_dir.name) / "flow.png"
        cleaned = Path(self.temp_dir.name) / "flow_cleaned.png"
        before_image = QImage(24, 24, QImage.Format.Format_RGB32)
        before_image.fill(0xAA0000)
        self.assertTrue(before_image.save(str(source)))
        after_image = QImage(24, 24, QImage.Format.Format_RGB32)
        after_image.fill(0x00AA00)
        self.assertTrue(after_image.save(str(cleaned)))

        tab = WatermarkTab()
        tab.on_files_selected([source])

        preview_tabs = tab.findChild(QTabWidget, "watermark_preview_tabs")
        self.assertIsNotNone(preview_tabs)
        self.assertEqual(preview_tabs.count(), 2)
        self.assertEqual(preview_tabs.tabText(0), "Trước")
        self.assertEqual(preview_tabs.tabText(1), "Sau")
        self.assertEqual(preview_tabs.currentIndex(), 0)

        tab.on_file_processed(1, 1, source.name, True, str(cleaned))

        self.assertEqual(preview_tabs.currentIndex(), 1)
        self.assertIsNotNone(tab.lbl_preview_clean.pixmap())

    def test_watermark_delete_selected_row_updates_list_and_saved_state(self):
        first = Path(self.temp_dir.name) / "first.png"
        second = Path(self.temp_dir.name) / "second.png"
        first.write_bytes(b"not-a-real-image")
        second.write_bytes(b"not-a-real-image")
        output_dir = Path(self.temp_dir.name) / "watermark"
        output_dir.mkdir()

        tab = WatermarkTab()
        tab.configure_standalone(self.store, output_dir)
        tab.on_files_selected([first, second])

        self.assertFalse(tab.btn_delete_selected.isEnabled())
        tab.table.selectRow(1)
        self.assertTrue(tab.btn_delete_selected.isEnabled())

        tab.btn_delete_selected.click()

        self.assertEqual(tab.selected_files, [first])
        self.assertEqual(tab.table.rowCount(), 1)
        self.assertEqual(tab.lbl_file_count.text(), "1 ảnh")
        self.assertEqual(self.store.load_watermark()["files"], [first])
        self.assertEqual(tab.table.currentRow(), 0)
        self.assertTrue(tab.btn_delete_selected.isEnabled())

    def test_tts_sidebar_mode_restores_configuration_without_project(self):
        output_dir = Path(self.temp_dir.name) / "tts"
        output_dir.mkdir()
        self.store.save_tts(
            {
                "script": "Nội dung độc lập",
                "provider": "elevenlabs",
                "voice_id": "voice-sidebar",
                "model": "eleven_flash_v2_5",
                "language": "vi",
                "stability": 42,
                "similarity": 73,
                "speed": 108,
                "export_srt": False,
                "subtab": 0,
            }
        )

        with patch("app.ui.tts_tab.QMediaPlayer", _SilentMediaPlayer), patch(
            "app.ui.tts_tab.QAudioOutput", _SilentAudioOutput
        ), patch(
            "app.ui.voice_lookup_tab.QMediaPlayer", _SilentMediaPlayer
        ), patch(
            "app.ui.voice_lookup_tab.QAudioOutput", _SilentAudioOutput
        ):
            tab = TTSTab()
            tab.configure_standalone(self.store, output_dir)

            self.assertIsNone(tab.project)
            self.assertEqual(tab.tool_title.text(), "Tạo Voice TTS")
            header_texts = [
                label.text() for label in tab.tool_header.findChildren(QLabel)
            ]
            self.assertNotIn(
                "Soạn nội dung, chọn giọng và lưu mỗi lượt trong một thư mục riêng.",
                header_texts,
            )
            self.assertFalse(
                any(text.startswith("Tự động lưu") for text in header_texts)
            )
            self.assertEqual(tab.txt_input.toPlainText(), "Nội dung độc lập")
            self.assertEqual(tab.edit_voice_id.text(), "voice-sidebar")
            self.assertEqual(tab.combo_model.currentText(), "eleven_flash_v2_5")
            self.assertEqual(tab.slider_sp.value(), 108)
            self.assertFalse(tab.chk_srt.isChecked())
            self.assertTrue(tab.btn_to_video.isHidden())
            self.assertEqual(tab.standalone_output_dir, output_dir)
            self.assertRegex(
                tab.edit_output_name.text(), r"^voice_\d{8}_\d{6}$"
            )
            self.assertEqual(tab.lbl_output_path.text(), str(output_dir))
            self.assertTrue(tab.btn_choose_output.isEnabled())
            self.assertIs(tab.btn_open_folder.parentWidget(), tab.output_controls)
            self.assertLessEqual(tab.tool_header.maximumHeight(), 72)

    def test_tts_sidebar_mode_flushes_pending_text_before_close(self):
        output_dir = Path(self.temp_dir.name) / "tts"
        output_dir.mkdir()
        with patch("app.ui.tts_tab.QMediaPlayer", _SilentMediaPlayer), patch(
            "app.ui.tts_tab.QAudioOutput", _SilentAudioOutput
        ), patch(
            "app.ui.voice_lookup_tab.QMediaPlayer", _SilentMediaPlayer
        ), patch(
            "app.ui.voice_lookup_tab.QAudioOutput", _SilentAudioOutput
        ):
            tab = TTSTab()
            tab.configure_standalone(self.store, output_dir)
            tab.txt_input.setPlainText("Nội dung vừa nhập")

            tab.flush_standalone_state()

            self.assertEqual(
                self.store.load_tts()["script"], "Nội dung vừa nhập"
            )

    def test_tts_sidebar_mode_can_change_the_base_output_folder(self):
        output_dir = Path(self.temp_dir.name) / "tts"
        selected_dir = Path(self.temp_dir.name) / "voice-exports"
        output_dir.mkdir()
        selected_dir.mkdir()

        with patch("app.ui.tts_tab.QMediaPlayer", _SilentMediaPlayer), patch(
            "app.ui.tts_tab.QAudioOutput", _SilentAudioOutput
        ), patch(
            "app.ui.voice_lookup_tab.QMediaPlayer", _SilentMediaPlayer
        ), patch(
            "app.ui.voice_lookup_tab.QAudioOutput", _SilentAudioOutput
        ):
            tab = TTSTab()
            tab.configure_standalone(self.store, output_dir)

            with patch(
                "app.ui.tts_tab.QFileDialog.getExistingDirectory",
                return_value=str(selected_dir),
            ):
                tab.choose_output_folder()

            self.assertEqual(tab.standalone_output_dir, selected_dir)
            self.assertEqual(tab.lbl_output_path.text(), str(selected_dir))
            self.assertEqual(self.store.load_tts()["output_dir"], selected_dir)

    def test_tts_failed_run_releases_an_empty_folder_for_retry(self):
        output_dir = Path(self.temp_dir.name) / "tts"
        output_dir.mkdir()

        with patch("app.ui.tts_tab.QMediaPlayer", _SilentMediaPlayer), patch(
            "app.ui.tts_tab.QAudioOutput", _SilentAudioOutput
        ), patch(
            "app.ui.voice_lookup_tab.QMediaPlayer", _SilentMediaPlayer
        ), patch(
            "app.ui.voice_lookup_tab.QAudioOutput", _SilentAudioOutput
        ), patch("app.ui.tts_tab.TTSWorker", _IdleTTSWorker), patch(
            "app.ui.tts_tab.QMessageBox.critical"
        ):
            tab = TTSTab()
            tab.configure_standalone(self.store, output_dir)
            tab.txt_input.setPlainText("Nội dung")
            tab.edit_voice_id.setText("voice-id")
            tab.edit_output_name.setText("voice_retry")

            tab.start_tts()

            run_dir = output_dir / "voice_retry"
            self.assertTrue(run_dir.is_dir())
            self.assertEqual(_IdleTTSWorker.last_instance.kwargs["output_dir"], run_dir)
            self.assertEqual(
                _IdleTTSWorker.last_instance.kwargs["output_filename"],
                "voice_retry.mp3",
            )
            self.assertFalse(tab.output_controls.isEnabled())

            tab.on_tts_finished(False, "", "", "Thiếu API key")

            self.assertFalse(run_dir.exists())
            self.assertEqual(tab.edit_output_name.text(), "voice_retry")
            self.assertTrue(tab.output_controls.isEnabled())

    def test_watermark_failed_run_releases_an_empty_folder_for_retry(self):
        source = Path(self.temp_dir.name) / "flow.png"
        output_dir = Path(self.temp_dir.name) / "watermark"
        source.write_bytes(b"image")
        output_dir.mkdir()

        with patch("app.ui.watermark_tab.WatermarkWorker", _IdleWatermarkWorker):
            tab = WatermarkTab()
            tab.configure_standalone(self.store, output_dir)
            tab.on_files_selected([source])
            tab.table.selectRow(0)
            tab.edit_output_name.setText("clean_retry")

            tab.start_processing()
            run_dir = output_dir / "clean_retry"
            self.assertTrue(run_dir.is_dir())
            self.assertFalse(tab.edit_output_name.isEnabled())
            self.assertFalse(tab.table.isEnabled())
            self.assertFalse(tab.btn_delete_selected.isEnabled())
            self.assertFalse(tab.action_clear.isEnabled())

            tab.on_finished_all(1, 0)

            self.assertFalse(run_dir.exists())
            self.assertEqual(tab.edit_output_name.text(), "clean_retry")
            self.assertTrue(tab.edit_output_name.isEnabled())
            self.assertTrue(tab.table.isEnabled())
            self.assertTrue(tab.btn_delete_selected.isEnabled())
            self.assertTrue(tab.action_clear.isEnabled())


if __name__ == "__main__":
    unittest.main()

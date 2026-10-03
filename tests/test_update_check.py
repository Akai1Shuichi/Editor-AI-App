import unittest
import sys
from unittest.mock import Mock, patch

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from app.update_check import UpdateCheckerThread, parse_update_response, is_newer_version
from app.ui.main_window import MainWindow
from app.ui.update_dialog import UpdateDialog
from app.version import APP_VERSION


class UpdateCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_newer_version_is_reported(self):
        payload = {
            "success": True,
            "data": {
                "hasNewVersion": True,
                "latestVersion": "1.2",
                "changeLog": "Sửa lỗi",
                "downloadLink": [
                    "https://github.com/Akai1Shuichi/Editor-AI-App/releases/download/v1.2/EditorVideoApp-v1.2-Windows.zip",
                ],
            },
        }
        self.assertEqual(
            parse_update_response(payload, current_version="1.1"),
            {
                "version": "1.2",
                "notes": "Sửa lỗi",
                "download_links": [
                    "https://github.com/Akai1Shuichi/Editor-AI-App/releases/download/v1.2/EditorVideoApp-v1.2-Windows.zip",
                ],
            },
        )

    def test_stale_server_version_is_ignored(self):
        payload = {
            "success": True,
            "data": {"hasNewVersion": True, "latestVersion": "1.1"},
        }
        self.assertIsNone(parse_update_response(payload, current_version="1.1"))
        self.assertTrue(is_newer_version("v1.2.0", "1.1"))
        self.assertFalse(is_newer_version("1.1.0", "1.1"))

    def test_up_to_date_response_with_null_download_link_does_not_start_update(self):
        payload = {
            "success": True,
            "message": "You are up to date.",
            "data": {
                "hasNewVersion": False,
                "latestVersion": "1.3",
                "changeLog": None,
                "downloadLink": None,
                "message": "You are up to date.",
            },
            "requestId": "f0d9082a-4bf0-4cdc-8c84-ad17874c178b",
        }
        self.assertIsNone(parse_update_response(payload, current_version="1.3"))

    def test_invalid_response_fails(self):
        with self.assertRaises(ValueError):
            parse_update_response({"success": False, "message": "Unavailable"}, current_version="1.1")

    def test_checker_posts_current_version_to_release_api(self):
        response = Mock()
        response.json.return_value = {"success": True, "data": {"hasNewVersion": False}}
        with patch("app.update_check.requests.post", return_value=response) as post:
            checker = UpdateCheckerThread()
            no_update = []
            checker.no_update.connect(lambda: no_update.append(True))
            checker.run()

        self.assertEqual(no_update, [True])
        self.assertEqual(post.call_args.args[0], "https://api.botocit.com/api/v1/update/check")
        self.assertEqual(
            post.call_args.kwargs["json"],
            {"code": "video-editor", "currentVersion": APP_VERSION},
        )

    def test_update_dialog_renders_html_changelog(self):
        notes = "<ul><li>Tạo video</li><li>Gỡ watermark</li></ul>"
        dialog = UpdateDialog("1.2", notes, "https://example.org/app-Windows.zip")
        self.assertIn(notes, dialog.details_label.text())
        self.assertEqual(dialog.details_label.textFormat(), Qt.TextFormat.RichText)

    def test_update_dialog_downloads_matching_windows_release(self):
        window = MainWindow()
        window._update_timer.stop()
        payload = {
            "version": "1.5",
            "notes": "Bản mới",
            "download_links": [
                "https://github.com/Akai1Shuichi/Editor-AI-App/releases/download/v1.5/EditorVideoApp-v1.5-Linux.zip",
                "https://cdn.example.org/releases/editor-build-42-Windows.zip",
            ],
        }
        with patch("app.ui.main_window.UpdateDownloadThread", FakeDownloadThread), \
             patch.object(sys, "platform", "win32"), \
             patch.object(sys, "frozen", True, create=True):
            def use_dialog():
                window._update_dialog.download_button.click()
                self.assertEqual(window._download_thread.url, payload["download_links"][1])
                self.assertTrue(window._update_dialog.progress_bar.isVisible())
                window._download_thread.staged.emit("/tmp/EditorVideoApp")
                window._download_thread.finished.emit()
                window._update_dialog.later_button.click()
            QTimer.singleShot(0, use_dialog)
            MainWindow._on_update_available(window, payload)
        window._staged_update = None
        window.close()

    def test_source_mode_does_not_check_for_updates_automatically(self):
        window = Mock()
        with patch.object(sys, "frozen", False, create=True):
            MainWindow._check_update_automatically(window)
        window._start_update_check.assert_not_called()

    def test_source_mode_manual_check_explains_packaged_app_requirement(self):
        window = Mock()
        with patch.object(sys, "frozen", False, create=True), \
             patch("app.ui.main_window.QMessageBox.information") as information:
            MainWindow._check_update_manually(window)
        window._start_update_check.assert_not_called()
        self.assertIn("bản đóng gói", information.call_args.args[2])


class FakeDownloadThread(QObject):
    progress = pyqtSignal(int)
    staged = pyqtSignal(str)
    failed = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url, target, parent=None):
        super().__init__(parent)
        self.url = url

    def start(self):
        pass

    def isRunning(self):
        return False


class UpdateDownloadUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_download_shows_blocking_progress_and_tracks_percent(self):
        window = MainWindow()
        window._update_timer.stop()
        dialog = UpdateDialog("1.5", "Bản mới", "https://example.org/app-Windows.zip", window)
        window._update_dialog = dialog
        dialog.show()
        with patch("app.ui.main_window.UpdateDownloadThread", FakeDownloadThread):
            window._start_update_download("https://example.org/app.zip", "1.5")
        self.assertTrue(dialog.isVisible())
        self.assertEqual(dialog.windowModality(), Qt.WindowModality.ApplicationModal)
        self.assertTrue(dialog.progress_bar.isVisible())
        self.assertFalse(dialog.download_button.isVisible())
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        self.assertTrue(dialog.isVisible())
        dialog.close()
        self.assertTrue(dialog.isVisible())
        window._download_thread.progress.emit(42)
        self.assertEqual(dialog.progress_bar.value(), 42)
        dialog.show_error("test")
        dialog.close()
        window.close()

    def test_success_offers_restart_after_download_finishes(self):
        window = MainWindow()
        window._update_timer.stop()
        dialog = UpdateDialog("1.5", "Bản mới", "https://example.org/app-Windows.zip", window)
        window._update_dialog = dialog
        dialog.show()
        with patch("app.ui.main_window.UpdateDownloadThread", FakeDownloadThread), \
             patch.object(window, "close") as close:
            window._start_update_download("https://example.org/app.zip", "1.5")
            window._download_thread.staged.emit("/tmp/EditorVideoApp")
            self.assertTrue(dialog.progress_bar.isVisible())
            window._download_thread.finished.emit()
            self.assertEqual(dialog.download_button.text(), "Cập nhật và khởi động lại")
            self.assertTrue(dialog.download_button.isVisible())
            dialog.restart_requested.connect(window.close)
            dialog.download_button.click()
            close.assert_called_once_with()
        window._update_dialog = None
        window._staged_update = None
        window.close()

    def test_deferred_update_waits_for_app_close(self):
        window = MainWindow()
        window._update_timer.stop()
        dialog = UpdateDialog("1.5", "Bản mới", "https://example.org/app-Windows.zip", window)
        window._update_dialog = dialog
        dialog.show()
        with patch("app.ui.main_window.UpdateDownloadThread", FakeDownloadThread), \
             patch.object(window, "close") as close:
            window._start_update_download("https://example.org/app.zip", "1.5")
            window._download_thread.staged.emit("/tmp/EditorVideoApp")
            window._download_thread.finished.emit()
            dialog.later_button.click()
            close.assert_not_called()
            self.assertEqual(str(window._staged_update), "/tmp/EditorVideoApp")
        window._update_dialog = None
        window._staged_update = None
        window.close()


if __name__ == "__main__":
    unittest.main()

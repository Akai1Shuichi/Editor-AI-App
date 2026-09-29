import unittest
from unittest.mock import Mock, patch

from PyQt6.QtCore import Qt

from app.update_check import UpdateCheckerThread, parse_update_response, is_newer_version
from app.ui.main_window import MainWindow
from app.version import APP_VERSION


class UpdateCheckTests(unittest.TestCase):
    def test_newer_version_is_reported(self):
        payload = {
            "success": True,
            "data": {
                "hasNewVersion": True,
                "latestVersion": "1.2",
                "changeLog": "Sửa lỗi",
            },
        }
        self.assertEqual(
            parse_update_response(payload, current_version="1.1"),
            {"version": "1.2", "notes": "Sửa lỗi"},
        )

    def test_stale_server_version_is_ignored(self):
        payload = {
            "success": True,
            "data": {"hasNewVersion": True, "latestVersion": "1.1"},
        }
        self.assertIsNone(parse_update_response(payload, current_version="1.1"))
        self.assertTrue(is_newer_version("v1.2.0", "1.1"))
        self.assertFalse(is_newer_version("1.1.0", "1.1"))

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
        window = Mock()
        with patch("app.ui.main_window.QMessageBox") as message_box:
            MainWindow._on_update_available(window, {"version": "1.2", "notes": notes})

        dialog = message_box.return_value
        dialog.setTextFormat.assert_called_once_with(Qt.TextFormat.RichText)
        self.assertIn(notes, dialog.setText.call_args.args[0])


if __name__ == "__main__":
    unittest.main()

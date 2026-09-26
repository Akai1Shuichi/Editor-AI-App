import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.update_download import update_package_filename
from app.updater import UpdateDownloaderThread, UpdateDialog


class ManualUpdateDownloadTests(unittest.TestCase):
    def test_download_endpoint_without_zip_name_uses_zip_fallback(self):
        """Catches a redirected /update/download URL being saved as extensionless 'download'."""
        filename = update_package_filename(
            "http://localhost:3000/api/v1/update/download?code=s-editor&versionName=1.1&os=windows",
            None,
            "EditorVideoAI-update.zip",
        )

        self.assertEqual(filename, "EditorVideoAI-update.zip")

    def test_download_saves_zip_beside_running_app_without_changing_executable(self):
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary)
            executable = install / "EditorVideoApp.exe"
            executable.write_bytes(b"version 1.0")
            response = MagicMock()
            response.url = "https://example.com/update/download"
            response.headers = {"Content-Disposition": 'attachment; filename="EditorVideoApp-v1.1-Windows.zip"', "Content-Length": "3"}
            response.iter_content.return_value = [b"zip"]
            response.__enter__.return_value = response

            with (
                patch("app.updater.sys.frozen", True, create=True),
                patch("app.updater.sys.executable", str(executable)),
                patch("app.core.telemetry.api_request", return_value=response),
            ):
                downloader = UpdateDownloaderThread("https://example.com/update/download", "EditorVideoAI-update.zip")
                downloaded = []
                downloader.finished.connect(downloaded.append)
                downloader.run()

            package = install / "EditorVideoApp-v1.1-Windows.zip"
            self.assertEqual(package.read_bytes(), b"zip")
            self.assertEqual(executable.read_bytes(), b"version 1.0")
            self.assertEqual(downloaded, [str(package)])

    def test_download_completion_closes_app_without_installing_package(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        info = {"version": "1.1", "current_version": "1.0", "os_name": "Windows", "download_url": "https://example.com/update/download"}
        dialog = UpdateDialog(info)
        with (
            patch("app.updater.QMessageBox.information") as message,
            patch("app.updater.QMessageBox.warning"),
            patch.object(app, "quit") as quit_app,
        ):
            dialog._download_finished("C:/Program Files/EditorVideoApp/EditorVideoApp-v1.1-Windows.zip")

        self.assertIn("EditorVideoApp-v1.1-Windows.zip", message.call_args.args[2])
        quit_app.assert_called_once()


if __name__ == "__main__":
    unittest.main()

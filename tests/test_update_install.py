import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.update_install import (
    apply_staged_update, download_and_stage, launch_update_helper,
    run_update_helper, select_download_url,
)


WINDOWS_URL = (
    "https://github.com/Akai1Shuichi/Editor-AI-App/releases/download/"
    "v1.5/EditorVideoApp-v1.5-Windows.zip"
)


class UpdateInstallTests(unittest.TestCase):
    def test_selects_platform_link_from_api_without_assuming_release_host_or_version(self):
        links = [
            "https://[invalid",
            "https://github.com/Akai1Shuichi/Editor-AI-App/releases/download/v1.5/EditorVideoApp-v1.5-Linux.zip",
            "http://downloads.example/app-Windows.zip",
            "https://cdn.example.org/files/editor-build-42-Windows.zip?token=abc",
        ]
        self.assertEqual(
            select_download_url(links, platform="win32"),
            "https://cdn.example.org/files/editor-build-42-Windows.zip?token=abc",
        )
        self.assertIsNone(select_download_url(links, platform="darwin"))

    def test_download_stages_executable_next_to_installed_copy(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("EditorVideoApp.exe", b"new executable")
            bundle.writestr("install.txt", b"guide")

        class Response:
            headers = {"Content-Length": str(len(archive.getvalue()))}

            def raise_for_status(self):
                pass

            def iter_content(self, chunk_size):
                yield archive.getvalue()

            def close(self):
                pass

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "EditorVideoApp.exe"
            target.write_bytes(b"old executable")
            with patch("app.update_install.requests.get", return_value=Response()):
                staged = download_and_stage(WINDOWS_URL, target)
            self.assertEqual(staged.read_bytes(), b"new executable")
            self.assertEqual(target.read_bytes(), b"old executable")

    def test_download_requires_an_installed_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "EditorVideoApp.exe"
            with patch("app.update_install.requests.get") as get:
                with self.assertRaises(ValueError):
                    download_and_stage(WINDOWS_URL, target)
            self.assertFalse(target.exists())
            get.assert_not_called()

    def test_replaces_installed_copy_without_leaving_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "EditorVideoApp.exe"
            staged = Path(directory) / "new.exe"
            target.write_bytes(b"old executable")
            staged.write_bytes(b"new executable")
            apply_staged_update(target, staged)
            self.assertEqual(target.read_bytes(), b"new executable")
            self.assertFalse((Path(directory) / "EditorVideoApp.exe.previous").exists())

    def test_failed_replacement_keeps_old_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "EditorVideoApp.exe"
            staged = Path(directory) / "new.exe"
            target.write_bytes(b"old executable")
            staged.write_bytes(b"new executable")
            real_replace = os.replace

            def replace(source, destination):
                if Path(source) == staged and Path(destination) == target:
                    raise OSError("disk error")
                return real_replace(source, destination)

            with patch("app.update_install.os.replace", side_effect=replace):
                with self.assertRaises(OSError):
                    apply_staged_update(target, staged)
            self.assertEqual(target.read_bytes(), b"old executable")
            self.assertFalse((Path(directory) / "EditorVideoApp.exe.previous").exists())

    def test_helper_applies_update_after_parent_has_exited(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "EditorVideoApp.exe"
            stage_dir = root / ".editor-update-test"
            stage_dir.mkdir()
            staged = stage_dir / "EditorVideoApp.exe"
            target.write_bytes(b"old executable")
            staged.write_bytes(b"new executable")
            with patch("app.update_install.subprocess.Popen") as launch:
                self.assertEqual(run_update_helper(target, staged, 99999999), 0)
            self.assertEqual(target.read_bytes(), b"new executable")
            self.assertFalse(stage_dir.exists())
            self.assertEqual(launch.call_args.args[0], [str(target)])

    def test_source_mode_cannot_launch_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "EditorVideoApp"
            staged = target.parent / ".editor-update-test" / target.name
            staged.parent.mkdir(parents=True)
            staged.write_bytes(b"new executable")
            with patch("app.update_install.sys.frozen", False, create=True):
                with self.assertRaises(RuntimeError):
                    launch_update_helper(target, staged)

    def test_retries_while_old_executable_is_temporarily_locked(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "EditorVideoApp.exe"
            staged = Path(directory) / "new.exe"
            target.write_bytes(b"old executable")
            staged.write_bytes(b"new executable")
            real_replace = os.replace
            attempts = 0

            def replace(source, destination):
                nonlocal attempts
                if Path(source) == staged and Path(destination) == target:
                    attempts += 1
                    if attempts == 1:
                        raise PermissionError("file is still running")
                return real_replace(source, destination)

            with patch("app.update_install.os.replace", side_effect=replace), \
                 patch("app.update_install.time.sleep"):
                apply_staged_update(target, staged)
            self.assertEqual(attempts, 2)
            self.assertEqual(target.read_bytes(), b"new executable")


if __name__ == "__main__":
    unittest.main()

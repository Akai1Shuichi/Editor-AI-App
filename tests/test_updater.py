import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.update_download import update_package_filename
from app.update_installer import create_update_helper, start_update_handoff


class InPlaceUpdateHelperTests(unittest.TestCase):
    def test_download_endpoint_without_zip_name_uses_zip_fallback(self):
        """Catches a redirected /update/download URL being saved as extensionless 'download'."""
        filename = update_package_filename(
            "http://localhost:3000/api/v1/update/download?code=s-editor&versionName=1.1&os=windows",
            None,
            "EditorVideoAI-update.zip",
        )

        self.assertEqual(filename, "EditorVideoAI-update.zip")

    def test_handoff_starts_detached_helper_for_the_running_packaged_app(self):
        """Catches the UI closing without a replacement helper being started."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / "staging"
            install = root / "installed"
            staging.mkdir()
            install.mkdir()
            (staging / "EditorVideoApp").write_text("new", encoding="utf-8")

            with (
                patch("app.update_installer.supports_in_place_update", return_value=True),
                patch("app.update_installer.installation_directory", return_value=install),
                patch("app.update_installer.subprocess.Popen") as popen,
            ):
                helper = start_update_handoff(staging, "EditorVideoApp")

            command = popen.call_args.args[0]
            self.assertEqual(command[:2], ["/bin/sh", str(helper)])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_linux_helper_replaces_installed_app_and_restarts_new_copy(self):
        """Catches an update that only opens a temporary download instead of replacing the install."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            install = root / "installed"
            staging = root / "staging"
            install.mkdir()
            staging.mkdir()
            old_app = install / "EditorVideoApp"
            old_app.write_text("#!/bin/sh\necho old\n", encoding="utf-8")
            old_app.chmod(0o755)
            new_app = staging / "EditorVideoApp"
            new_app_contents = "#!/bin/sh\nprintf new > \"$0.started\"\n"
            new_app.write_text(new_app_contents, encoding="utf-8")
            new_app.chmod(0o755)

            helper = create_update_helper(staging, install, "EditorVideoApp", platform_name="linux")
            completed = subprocess.run(
                ["/bin/sh", str(helper), "999999"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual((install / "EditorVideoApp").read_text(encoding="utf-8"), new_app_contents)
            self.assertEqual((install / "EditorVideoApp.started").read_text(encoding="utf-8"), "new")


if __name__ == "__main__":
    unittest.main()

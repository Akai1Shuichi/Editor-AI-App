import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QImage, QColor
from PyQt6.QtWidgets import QApplication

from app.core.project_manager import Project
from app.ui.watermark_tab import WatermarkTab


def save_image(path: Path):
    image = QImage(32, 24, QImage.Format.Format_RGB32)
    image.fill(QColor("blue"))
    assert image.save(str(path))


class WatermarkFolderSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.tab = WatermarkTab()
        self.addCleanup(self.tab.close)

    def choose(self, folder):
        with patch("app.ui.watermark_tab.QFileDialog.getExistingDirectory", return_value=str(folder)), \
             patch("app.ui.watermark_tab.QMessageBox.information") as information:
            self.tab.choose_folder()
        information.assert_not_called()

    def test_project_clean_folder_with_only_cleaned_images_is_accepted(self):
        project = Project(self.root / "project")
        images = [project.clean_images_dir / f"SC{i:02d}_20260929162829_cleaned.png"
                  for i in (1, 2)]
        for image in images:
            save_image(image)
        self.tab.set_project(project)
        self.tab.clear_file_list()

        self.choose(project.clean_images_dir)

        self.assertEqual(self.tab.selected_files, images)
        self.assertEqual(self.tab.table.rowCount(), 2)
        self.assertEqual(self.tab.table.item(0, 1).text(), "✓ Sẵn sàng")
        self.assertIn("ảnh sạch", self.tab.status_lbl.text())

    def test_standalone_clean_folder_is_accepted_and_mixed_folder_prefers_raw(self):
        folder = self.root / "clean"
        folder.mkdir()
        cleaned = folder / "SC01_cleaned.png"
        save_image(cleaned)
        self.choose(folder)
        self.assertEqual(self.tab.selected_files, [cleaned])
        self.assertEqual(self.tab.table.item(0, 1).text(), "✓ Sẵn sàng")

        raw = folder / "SC01.png"
        save_image(raw)
        self.tab.clear_file_list()
        self.choose(folder)
        self.assertEqual(self.tab.selected_files, [raw])
        self.assertEqual(self.tab.table.item(0, 1).text(), "Chờ")


if __name__ == "__main__":
    unittest.main()

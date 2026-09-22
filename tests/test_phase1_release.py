import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class Phase1ReleaseTests(unittest.TestCase):
    def test_watermark_layout_uses_fixed_sixty_forty_columns_without_splitter(self):
        """Catches the watermark workspace reverting to a draggable splitter."""
        source = (ROOT / "app" / "ui" / "watermark_tab.py").read_text()
        module = ast.parse(source)
        init_ui = next(
            node
            for node in ast.walk(module)
            if isinstance(node, ast.FunctionDef) and node.name == "init_ui"
        )
        calls = [
            node for node in ast.walk(init_ui) if isinstance(node, ast.Call)
        ]
        constructor_names = {
            node.func.id for node in calls if isinstance(node.func, ast.Name)
        }
        stretch_values = [
            [argument.value for argument in node.args]
            for node in calls
            if isinstance(node.func, ast.Attribute) and node.func.attr == "setStretch"
        ]

        self.assertNotIn("QSplitter", constructor_names)
        self.assertIn("QHBoxLayout", constructor_names)
        self.assertIn([0, 6], stretch_values)
        self.assertIn([1, 4], stretch_values)

    def test_application_and_packager_use_the_ico_asset(self):
        main_source = (ROOT / "app" / "main.py").read_text()
        spec_source = (ROOT / "editor_video_app.spec").read_text()

        self.assertIn("QIcon", main_source)
        self.assertIn('_asset_path("icon.ico")', main_source)
        self.assertIn('"assets" / "icon.ico"', spec_source)
        self.assertIn("icon=", spec_source)

    def test_footer_includes_clickable_zalo_support_link(self):
        source = (ROOT / "app" / "ui" / "main_window.py").read_text()

        self.assertIn("https://zalo.me/g/2h4r4fbobrg66e9haa3q", source)
        self.assertIn("setOpenExternalLinks(True)", source)

    def test_watermark_list_has_direct_clear_all_button_without_overflow_menu(self):
        source = (ROOT / "app" / "ui" / "watermark_tab.py").read_text()

        self.assertIn('QPushButton("Xóa hết")', source)
        self.assertNotIn("btn_list_menu", source)

    def test_main_window_import_does_not_load_later_phase_modules(self):
        source = (ROOT / "app" / "ui" / "main_window.py").read_text()
        module = ast.parse(source)
        imports = {
            node.module
            for node in ast.walk(module)
            if isinstance(node, ast.ImportFrom) and node.module
        }

        self.assertTrue(
            {
                "app.ui.project_workspace",
                "app.ui.tts_tab",
                "app.ui.settings_tab",
                "app.ui.pricing_tab",
            }.isdisjoint(imports),
            "Phase-1 must not import modules scheduled for later releases.",
        )

    def test_packaging_bundles_video_runtime(self):
        spec = (ROOT / "editor_video_app.spec").read_text()
        self.assertIn("imageio_ffmpeg", spec)


if __name__ == "__main__":
    unittest.main()

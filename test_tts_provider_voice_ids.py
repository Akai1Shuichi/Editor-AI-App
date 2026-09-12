import tempfile
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from app import config
from app.core.project_manager import Project
from app.ui.tts_tab import TTSTab


def select_provider(tab: TTSTab, provider: str) -> None:
    for index in range(tab.combo_provider.count()):
        if tab.combo_provider.itemData(index) == provider:
            tab.combo_provider.setCurrentIndex(index)
            return
    raise AssertionError(f"Provider not found: {provider}")


class MemoryTTSStore:
    def __init__(self):
        self.state = {}

    def load_tts(self):
        return dict(self.state)

    def save_tts(self, state):
        self.state = dict(state)


class ProviderVoiceIDTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_switching_provider_restores_its_own_voice_id(self):
        tab = TTSTab()
        tab.set_selected_voice_id("eleven-id")

        select_provider(tab, "minimax")
        self.assertEqual(tab.current_voice_id(), "")
        tab.set_selected_voice_id("minimax-id")

        select_provider(tab, "capcut")
        self.assertEqual(tab.current_voice_id(), "")
        tab.set_selected_voice_id("capcut-id")

        select_provider(tab, "elevenlabs")
        self.assertEqual(tab.current_voice_id(), "eleven-id")
        select_provider(tab, "minimax")
        self.assertEqual(tab.current_voice_id(), "minimax-id")
        select_provider(tab, "capcut")
        self.assertEqual(tab.current_voice_id(), "capcut-id")

    def test_voice_selector_opens_lookup_and_displays_the_picked_voice(self):
        tab = TTSTab()

        self.assertEqual(tab.combo_voice.currentText(), "Chọn giọng nói…")
        api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            tab.combo_voice.showPopup()
            self.assertEqual(tab.tab_widget.currentIndex(), 1)
        finally:
            config.VIBI_API_KEY = api_key

        tab.set_selected_voice_id("voice-123", "Giọng Lan")
        self.assertEqual(tab.combo_voice.currentText(), "Giọng Lan")
        self.assertEqual(tab.combo_voice.currentData(), "voice-123")
        self.assertEqual(tab.lbl_status.text(), "Sẵn sàng.")

    def test_all_providers_keep_the_elevenlabs_parameter_controls(self):
        """Changing provider must not turn the shared controls into pitch/volume."""
        tab = TTSTab()

        for provider in ("minimax", "capcut"):
            with self.subTest(provider=provider):
                select_provider(tab, provider)

                self.assertEqual(tab.lbl_st.text(), "Độ ổn định:")
                self.assertEqual(tab.slider_st.minimum(), 0)
                self.assertEqual(tab.slider_st.maximum(), 100)
                self.assertEqual(tab.slider_st.value(), 50)
                self.assertEqual(tab.lbl_st_val.text(), "0.50")

                self.assertEqual(tab.lbl_sim.text(), "Độ tương đồng:")
                self.assertTrue(tab.slider_sim.isEnabled())
                self.assertEqual(tab.slider_sim.minimum(), 0)
                self.assertEqual(tab.slider_sim.maximum(), 100)
                self.assertEqual(tab.slider_sim.value(), 75)
                self.assertEqual(tab.lbl_sim_val.text(), "0.75")

                self.assertEqual(tab.slider_sp.minimum(), 70)
                self.assertEqual(tab.slider_sp.maximum(), 150)
                self.assertEqual(tab.slider_sp.value(), 100)
                self.assertEqual(tab.lbl_sp_val.text(), "1.00x")

    def test_all_provider_voice_ids_survive_project_reload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "demo"
            project = Project(project_path, {"name": "Demo"})
            tab = TTSTab()
            tab.set_project(project)

            tab.set_selected_voice_id("eleven-project-id")
            select_provider(tab, "minimax")
            tab.set_selected_voice_id("minimax-project-id")
            select_provider(tab, "capcut")
            tab.set_selected_voice_id("capcut-project-id")
            tab.save_current_state()

            restored_tab = TTSTab()
            restored_tab.set_project(Project(project_path))

            select_provider(restored_tab, "elevenlabs")
            self.assertEqual(restored_tab.current_voice_id(), "eleven-project-id")
            select_provider(restored_tab, "minimax")
            self.assertEqual(restored_tab.current_voice_id(), "minimax-project-id")
            select_provider(restored_tab, "capcut")
            self.assertEqual(restored_tab.current_voice_id(), "capcut-project-id")

    def test_legacy_voice_id_is_assigned_to_its_saved_provider(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Project(
                Path(temp_dir) / "legacy",
                {
                    "name": "Legacy",
                    "tts_settings": {
                        "provider": "minimax",
                        "voice_id": "legacy-minimax-id",
                    },
                },
            )
            tab = TTSTab()
            tab.set_project(project)

            self.assertEqual(tab.current_voice_id(), "legacy-minimax-id")
            select_provider(tab, "elevenlabs")
            self.assertEqual(tab.current_voice_id(), "")
            select_provider(tab, "minimax")
            self.assertEqual(tab.current_voice_id(), "legacy-minimax-id")

    def test_project_without_tts_settings_does_not_inherit_previous_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tab = TTSTab()
            first_project = Project(
                Path(temp_dir) / "first",
                {
                    "name": "First",
                    "tts_settings": {
                        "provider": "minimax",
                        "voice_ids": {
                            "elevenlabs": "first-eleven-id",
                            "minimax": "first-minimax-id",
                            "capcut": "first-capcut-id",
                        },
                    },
                },
            )
            tab.set_project(first_project)

            tab.set_project(Project(Path(temp_dir) / "empty", {"name": "Empty"}))

            select_provider(tab, "elevenlabs")
            self.assertEqual(tab.current_voice_id(), "")
            select_provider(tab, "minimax")
            self.assertEqual(tab.current_voice_id(), "")
            select_provider(tab, "capcut")
            self.assertEqual(tab.current_voice_id(), "")

    def test_all_provider_voice_ids_survive_standalone_reload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = MemoryTTSStore()
            tab = TTSTab()
            tab.configure_standalone(store, Path(temp_dir))

            tab.set_selected_voice_id("eleven-standalone-id")
            select_provider(tab, "minimax")
            tab.set_selected_voice_id("minimax-standalone-id")
            select_provider(tab, "capcut")
            tab.set_selected_voice_id("capcut-standalone-id")
            tab.flush_standalone_state()

            restored_tab = TTSTab()
            restored_tab.configure_standalone(store, Path(temp_dir))

            select_provider(restored_tab, "elevenlabs")
            self.assertEqual(restored_tab.current_voice_id(), "eleven-standalone-id")
            select_provider(restored_tab, "minimax")
            self.assertEqual(restored_tab.current_voice_id(), "minimax-standalone-id")
            select_provider(restored_tab, "capcut")
            self.assertEqual(restored_tab.current_voice_id(), "capcut-standalone-id")

    def test_restoring_a_standalone_session_does_not_show_a_restore_status(self):
        store = MemoryTTSStore()
        store.state = {"script": "Nội dung đã lưu"}

        tab = TTSTab()
        tab.configure_standalone(store, Path(tempfile.gettempdir()))

        self.assertEqual(tab.lbl_status.text(), "Sẵn sàng.")


if __name__ == "__main__":
    unittest.main()

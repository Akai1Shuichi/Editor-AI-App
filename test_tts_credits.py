import unittest

from PyQt6.QtWidgets import QApplication

from app import config
from app.core.tts_credits import estimate_tts_credits, format_credit_summary
from app.ui.main_window import MainWindow
from app.ui.tts_tab import TTSTab


class EstimateTTSCreditsTests(unittest.TestCase):
    def test_elevenlabs_turbo_and_flash_cost_half_credit_per_character(self):
        self.assertEqual(estimate_tts_credits("abc", "elevenlabs", "eleven_turbo_v2_5"), 2)
        self.assertEqual(estimate_tts_credits("abc", "elevenlabs", "eleven_flash_v2_5"), 2)

    def test_other_elevenlabs_models_cost_one_credit_per_character(self):
        self.assertEqual(estimate_tts_credits("abc", "elevenlabs", "eleven_v3"), 3)

    def test_minimax_turbo_costs_point_six_and_hd_costs_one_per_character(self):
        self.assertEqual(estimate_tts_credits("ab", "minimax", "speech-2.8-turbo"), 2)
        self.assertEqual(estimate_tts_credits("ab", "minimax", "speech-2.8-hd"), 2)

    def test_capcut_costs_point_zero_one_credit_per_character(self):
        self.assertEqual(estimate_tts_credits("a" * 101, "capcut", "capcut"), 2)

    def test_empty_text_costs_zero_credits(self):
        self.assertEqual(estimate_tts_credits("", "elevenlabs", "eleven_v3"), 0)


class FormatCreditSummaryTests(unittest.TestCase):
    def test_formats_character_count_estimate_and_current_balance(self):
        summary = format_credit_summary(
            "a" * 202,
            provider="elevenlabs",
            model="eleven_flash_v2_5",
            balance=119_863,
        )

        self.assertEqual(summary, "202 chars · 101/119,863 credits")

    def test_uses_placeholder_until_balance_is_available(self):
        summary = format_credit_summary("", "elevenlabs", "eleven_v3", None)

        self.assertEqual(summary, "0 chars · 0/-- credits")


class TTSCreditSummaryWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_starts_with_an_empty_summary_while_balance_is_loading(self):
        tab = TTSTab()

        self.assertEqual(tab.lbl_char_count.text(), "0 chars · 0/-- credits")

    def test_updates_summary_for_balance_text_and_model_changes(self):
        tab = TTSTab()

        tab.set_credit_balance(119_863)
        tab.txt_input.setPlainText("abc")
        self.assertEqual(tab.lbl_char_count.text(), "3 chars · 3/119,863 credits")

        tab.combo_model.setCurrentText("eleven_flash_v2_5")
        self.assertEqual(tab.lbl_char_count.text(), "3 chars · 2/119,863 credits")

    def test_help_icon_explains_every_credit_rate(self):
        tab = TTSTab()

        tooltip = tab.lbl_credit_help.toolTip()
        self.assertIn("ElevenLabs Turbo/Flash: 0.5", tooltip)
        self.assertIn("ElevenLabs các model khác: 1", tooltip)
        self.assertIn("MiniMax Turbo: 0.6", tooltip)
        self.assertIn("MiniMax HD: 1", tooltip)
        self.assertIn("CapCut: 0.01", tooltip)

    def test_credit_summary_is_readable_and_sits_below_the_editor(self):
        tab = TTSTab()
        tab.resize(1100, 760)
        tab.show()
        self.app.processEvents()

        self.assertGreater(
            tab.lbl_char_count.geometry().top(),
            tab.txt_input.geometry().bottom(),
        )
        self.assertGreaterEqual(tab.lbl_char_count.font().pixelSize(), 13)
        self.assertGreaterEqual(tab.lbl_credit_help.width(), 18)
        self.assertGreaterEqual(tab.lbl_credit_help.height(), 18)

    def test_account_update_reaches_both_tts_views(self):
        original_key = config.VIBI_API_KEY
        config.VIBI_API_KEY = ""
        try:
            window = MainWindow()
        finally:
            config.VIBI_API_KEY = original_key

        window.on_account_updated({"credit_balance": 119_863})

        expected = "0 chars · 0/119,863 credits"
        self.assertEqual(window.tts_tab.lbl_char_count.text(), expected)
        self.assertEqual(
            window.project_workspace.tts_tab.lbl_char_count.text(), expected
        )


if __name__ == "__main__":
    unittest.main()

import unittest

from PyQt6.QtWidgets import QApplication

from app import config
from app.ui.settings_tab import SettingsTab


class SettingsApiKeyHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_api_key_purchase_help_links_to_the_service_bot(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            tab = SettingsTab()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertIn("Mua API Voice Key tại đây", tab.lbl_buy_api_key.text())
        self.assertIn("@DichVuIT_bot", tab.lbl_buy_api_key.text())
        self.assertIn("https://t.me/DichVuIT_bot", tab.lbl_buy_api_key.text())
        self.assertTrue(tab.lbl_buy_api_key.openExternalLinks())


if __name__ == "__main__":
    unittest.main()

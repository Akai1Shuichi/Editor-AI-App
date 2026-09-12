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

    def test_support_links_include_zalo_and_telegram_icons(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            tab = SettingsTab()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertFalse(tab.lbl_telegram_icon.pixmap().isNull())
        self.assertFalse(tab.lbl_zalo_icon.pixmap().isNull())
        self.assertIn("https://zalo.me/g/2h4r4fbobrg66e9haa3q", tab.lbl_zalo_help.text())
        self.assertTrue(tab.lbl_zalo_help.openExternalLinks())


if __name__ == "__main__":
    unittest.main()

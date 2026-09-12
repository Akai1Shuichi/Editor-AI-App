import unittest

from PyQt6.QtWidgets import QApplication

from app import config
from app.ui.main_window import MainWindow
from app.ui.settings_tab import SettingsTab


class SettingsApiKeyHelpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_footer_shows_the_api_key_purchase_link_on_every_page(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            window = MainWindow()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertIn("Shop AI:", window.lbl_footer_telegram.text())
        self.assertIn("@DichVuIT_bot", window.lbl_footer_telegram.text())
        self.assertIn("https://t.me/DichVuIT_bot", window.lbl_footer_telegram.text())
        self.assertTrue(window.lbl_footer_telegram.openExternalLinks())
        self.assertIs(window.footer_support.parentWidget(), window.app_footer)
        self.assertGreaterEqual(window.app_footer.minimumHeight(), 56)
        self.assertFalse(hasattr(window, "lbl_footer_title"))
        window.show()
        self.app.processEvents()
        self.assertGreater(window.app_footer.width(), window.sidebar_footer.width())

    def test_settings_links_to_vibi_for_a_test_api_key(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            tab = SettingsTab()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertIn("Lấy API Key test tại đây", tab.lbl_vibi_test_key.text())
        self.assertIn("https://vibi.pro", tab.lbl_vibi_test_key.text())
        self.assertTrue(tab.lbl_vibi_test_key.openExternalLinks())

    def test_buy_api_key_button_opens_the_pricing_page(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            window = MainWindow()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertEqual(window.settings_tab.btn_buy_api_key.text(), "Mua API Key")
        self.assertEqual(window.settings_tab.btn_buy_api_key.objectName(), "btn_buy_api")
        window.switch_page(3)
        window.show()
        self.app.processEvents()
        self.assertGreater(
            window.settings_tab.btn_buy_api_key.geometry().top(),
            window.settings_tab.info_box.geometry().bottom(),
        )
        window.settings_tab.btn_buy_api_key.click()
        self.assertIs(window.stack.currentWidget(), window.pricing_tab)

    def test_footer_support_links_include_zalo_and_telegram_icons(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            window = MainWindow()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertFalse(window.lbl_footer_telegram_icon.pixmap().isNull())
        self.assertFalse(window.lbl_footer_zalo_icon.pixmap().isNull())
        self.assertIn("https://zalo.me/g/2h4r4fbobrg66e9haa3q", window.lbl_footer_zalo.text())
        self.assertTrue(window.lbl_footer_zalo.openExternalLinks())
        self.assertFalse(hasattr(window.settings_tab, "lbl_buy_api_key"))

    def test_pricing_sidebar_opens_the_discounted_bot_purchase_offer(self):
        original_api_key = config.VIBI_API_KEY
        try:
            config.VIBI_API_KEY = ""
            window = MainWindow()
        finally:
            config.VIBI_API_KEY = original_api_key

        self.assertEqual(window.nav_buttons[3].text(), "⚙  Cài đặt")
        self.assertEqual(window.nav_buttons[4].text(), "🏷  Bảng giá")
        window.btn_nav_pricing.click()
        self.assertIs(window.stack.currentWidget(), window.pricing_tab)
        self.assertEqual(window.pricing_tab.lbl_pricing_title.text(), "Bảng giá")
        self.assertFalse(hasattr(window.pricing_tab, "lbl_pricing_telegram_icon"))
        self.assertFalse(hasattr(window.pricing_tab, "lbl_pricing_subtitle"))
        self.assertFalse(hasattr(window.pricing_tab, "lbl_bot_offer_title"))
        self.assertEqual(
            window.pricing_tab.lbl_bot_offer_name.text(),
            "ElevenLabs Redeem 131K Credit · Sale 30%",
        )
        self.assertEqual(window.pricing_tab.lbl_bot_offer_original_price.text(), "92.000đ")
        self.assertEqual(window.pricing_tab.lbl_bot_offer_sale_price.text(), "65.000đ")
        self.assertEqual(window.pricing_tab.lbl_bot_purchase_prefix.text(), "Mua tại")
        self.assertFalse(window.pricing_tab.lbl_bot_purchase_telegram_icon.pixmap().isNull())
        self.assertNotIn("Mua tại", window.pricing_tab.lbl_bot_purchase_link.text())
        self.assertIn("https://t.me/DichVuIT_bot", window.pricing_tab.lbl_bot_purchase_link.text())
        self.assertTrue(window.pricing_tab.lbl_bot_purchase_link.openExternalLinks())
        self.assertFalse(hasattr(window.settings_tab, "bot_offer"))


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QLabel, QPushButton

from app.ui.main_window import MainWindow
from app.ui.pricing_tab import PricingTab
from app.ui.project_workspace import ProjectWorkspace
from app.ui.tts_tab import TTSTab


class RestoredFeaturesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_project_tts_and_settings_are_reachable_from_sidebar(self):
        with patch("app.ui.pricing_tab.PricingTab.refresh_pricing"):
            window = MainWindow()
        try:
            labels = [button.text() for button in window.nav_buttons]
            for label in ("Dự án", "Tạo Voice TTS", "Cài đặt"):
                self.assertTrue(any(label in text for text in labels), label)

            self.assertIsInstance(window.project_workspace, ProjectWorkspace)
            self.assertIsInstance(window.tts_tab, TTSTab)
            self.assertIs(window.stack.widget(0), window.project_workspace)
            self.assertIs(window.stack.widget(2), window.tts_tab)
            self.assertIsNotNone(window.tts_tab.standalone_store)
            self.assertFalse(any(
                "Kịch Bản Cảnh" in button.text()
                for button in window.project_workspace.tts_tab.findChildren(QPushButton)
            ))

            for index, button in enumerate(window.nav_buttons):
                button.click()
                self.assertEqual(window.stack.currentIndex(), index)
                self.assertTrue(button.isChecked())

            window.on_account_updated({"credit_balance": 1200})
            self.assertEqual(window.tts_tab.credit_balance, 1200)
            self.assertEqual(window.project_workspace.tts_tab.credit_balance, 1200)
            self.assertIn("1,200", window.api_chip.text())
            self.assertIn("#34d399", window.api_chip.styleSheet())
            self.assertIn("#064e3b", window.api_chip.styleSheet())

            window.on_account_updated({"credit_balance": 0})
            self.assertNotIn("#34d399", window.api_chip.styleSheet())
        finally:
            window.close()

    def test_pricing_none_response_keeps_all_default_offers(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        try:
            tab._on_pricing_loaded(True, None, "")
            labels = [
                tab.offers_layout.itemAt(index).widget()
                .findChild(QLabel, "offer_label").text()
                for index in range(tab.offers_layout.count())
            ]
            self.assertEqual(labels, [
                "🔥 Google Pro 18 tháng",
                "🔥 ElevenLabs Redeem 131K Credit",
                "🔥 ElevenLabs Redeem 300K Credit",
            ])
            for index in (1, 2):
                offer = tab.offers_layout.itemAt(index).widget()
                self.assertEqual(offer.findChild(QLabel, "offer_sale").text(), "Sale 30%")
            self.assertFalse(tab.zalo_contact.isHidden())
        finally:
            tab.close()

    def test_pricing_api_offer_does_not_duplicate_redeem_default(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        try:
            tab.update_pricing_data([
                {"label": "🔥 ElevenLabs Redeem 131K Credit", "price": 50000},
            ])
            labels = [
                tab.offers_layout.itemAt(index).widget()
                .findChild(QLabel, "offer_label").text()
                for index in range(tab.offers_layout.count())
            ]
            self.assertEqual(labels.count("🔥 ElevenLabs Redeem 131K Credit"), 1)
            self.assertIn("🔥 ElevenLabs Redeem 300K Credit", labels)
        finally:
            tab.close()

    def test_pricing_network_error_still_shows_default_offers(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        try:
            tab._on_pricing_loaded(False, {}, "network error")
            labels = [
                tab.offers_layout.itemAt(index).widget()
                .findChild(QLabel, "offer_label").text()
                for index in range(tab.offers_layout.count())
            ]
            self.assertIn("🔥 ElevenLabs Redeem 131K Credit", labels)
            self.assertIn("🔥 ElevenLabs Redeem 300K Credit", labels)
        finally:
            tab.close()

    def test_pricing_empty_items_payload_shows_default_offers(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        try:
            tab._on_pricing_loaded(True, {"items": []}, "")
            self.assertEqual(tab.offers_layout.count(), 3)
        finally:
            tab.close()

    def test_pricing_google_offer_from_api_gets_fire_without_duplicate(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        try:
            tab.update_pricing_data([{"label": "Google Pro 18 tháng", "price": 55000}])
            labels = [
                tab.offers_layout.itemAt(index).widget()
                .findChild(QLabel, "offer_label").text()
                for index in range(tab.offers_layout.count())
            ]
            self.assertEqual(labels.count("🔥 Google Pro 18 tháng"), 1)
            self.assertNotIn("Google Pro 18 tháng", labels)
        finally:
            tab.close()


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import QUrl

from app.ui.pricing_tab import PricingTab, PricingFetchThread
from app.ui.main_window import MainWindow


class PricingTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_default_url_uses_botocit_products_endpoint(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        self.assertEqual(
            tab.pricing_url,
            "https://api.botocit.com/api/v2/telegram-buyer/products",
        )

    def test_telegram_click_opens_bot(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        with patch("app.ui.pricing_tab.QDesktopServices") as desktop_services:
            tab.lbl_bot_purchase_link.linkActivated.emit("https://t.me/DichVuIT_bot")

        self.assertFalse(tab.lbl_bot_purchase_link.openExternalLinks())
        desktop_services.openUrl.assert_called_once_with(QUrl("https://t.me/DichVuIT_bot"))

    def test_products_request_and_render(self):
        product = {
            "label": "Google Pro 18 tháng",
            "price": 55000,
            "old_price": 79000,
            "sale": 30,
        }
        with patch("app.ui.pricing_tab.requests.get") as get:
            get.return_value.json.return_value = [product]
            worker = PricingFetchThread("https://api.botocit.com/api/v2/telegram-buyer/products")
            received = []
            worker.result_ready.connect(lambda *args: received.append(args))
            worker.run()
        self.assertEqual(received, [(True, [product], "")])
        get.assert_called_once_with(worker.url, headers={"Accept": "application/json"}, timeout=10)

        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab.update_pricing_data(received[0][1])
        texts = [label.text() for label in tab.offers_container.findChildren(QLabel)]
        for expected in ("Google Pro 18 tháng", "Sale 30%", "79.000đ", "55.000đ"):
            self.assertIn(expected, texts)

    def test_empty_response_shows_default_product_without_prices(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab._on_pricing_loaded(True, [], "")
        self.assertEqual(tab.offers_layout.count(), 1)
        offer = tab.offers_layout.itemAt(0).widget()
        texts = [label.text() for label in offer.findChildren(QLabel)]
        self.assertIn("Google Pro 18 tháng", texts)
        self.assertIn("Sale 30%", texts)
        self.assertIsNone(offer.findChild(QLabel, "offer_price"))
        self.assertIsNone(offer.findChild(QLabel, "offer_old_price"))
        self.assertTrue(tab.lbl_status.isHidden())
        self.assertFalse(tab.zalo_contact.isHidden())
        zalo_link = tab.zalo_contact.findChild(QLabel, "zalo_purchase_link")
        self.assertIn("0867057221", zalo_link.text())
        self.assertIn("https://zalo.me/0867057221", zalo_link.text())
        self.assertTrue(zalo_link.openExternalLinks())
        self.assertFalse(tab.zalo_contact.findChild(QLabel, "zalo_purchase_icon").pixmap().isNull())

    def test_missing_google_product_keeps_other_items_and_adds_default(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab.update_pricing_data([{"label": "Gói khác", "price": 55000}])
        self.assertEqual(tab.offers_layout.count(), 2)
        default_offer = tab.offers_layout.itemAt(0).widget()
        other_offer = tab.offers_layout.itemAt(1).widget()
        self.assertEqual(default_offer.findChild(QLabel, "offer_label").text(), "Google Pro 18 tháng")
        self.assertIsNone(default_offer.findChild(QLabel, "offer_price"))
        self.assertEqual(other_offer.findChild(QLabel, "offer_label").text(), "Gói khác")
        self.assertEqual(other_offer.findChild(QLabel, "offer_price").text(), "55.000đ")
        self.assertFalse(tab.zalo_contact.isHidden())

    def test_google_product_from_api_is_not_duplicated(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab.update_pricing_data([
            {"label": "Gói khác", "price": 35000},
            {"label": "Google Pro 18 tháng", "price": 55000},
        ])
        self.assertEqual(tab.offers_layout.count(), 2)
        labels = [
            tab.offers_layout.itemAt(index).widget().findChild(QLabel, "offer_label").text()
            for index in range(tab.offers_layout.count())
        ]
        self.assertEqual(labels.count("Google Pro 18 tháng"), 1)
        self.assertTrue(tab.zalo_contact.isHidden())

    def test_failed_request_shows_error(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab._on_pricing_loaded(False, {}, "network error")
        self.assertIn("Không tải được", tab.lbl_status.text())

    def test_pricing_is_a_separate_sidebar_page_from_watermark_tabs(self):
        with patch.object(PricingTab, "refresh_pricing"):
            window = MainWindow()
        self.assertEqual(
            [window.watermark_pages.tabText(index) for index in range(window.watermark_pages.count())],
            ["Gỡ watermark Ảnh", "Gỡ watermark Video"],
        )
        self.assertIs(window.stack.widget(0), window.watermark_pages)
        self.assertIs(window.stack.widget(1), window.pricing_tab)
        self.assertIn("Shop AI", window.btn_nav_pricing.text())
        self.assertEqual(window.pricing_tab.lbl_pricing_title.text(), "Shop AI")

    def test_sidebar_switches_pages_and_marks_active_button(self):
        with patch.object(PricingTab, "refresh_pricing"):
            window = MainWindow()
        self.assertFalse(window.watermark_pages.tabBar().isHidden())
        self.assertEqual(len(window.nav_buttons), 2)

        window.btn_nav_pricing.click()
        self.assertIs(window.stack.currentWidget(), window.pricing_tab)
        self.assertTrue(window.btn_nav_pricing.isChecked())
        self.assertFalse(window.btn_nav_watermark.isChecked())

        window.btn_nav_watermark.click()
        self.assertIs(window.stack.currentWidget(), window.watermark_pages)
        window.watermark_pages.setCurrentIndex(1)
        self.assertIs(window.watermark_pages.currentWidget(), window.video_watermark_tab)
        self.assertTrue(window.btn_nav_watermark.isChecked())
        self.assertFalse(window.btn_nav_pricing.isChecked())


if __name__ == "__main__":
    unittest.main()

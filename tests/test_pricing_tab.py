import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel

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

    def test_products_request_and_render(self):
        product = {
            "label": "Google Pro 18 tháng",
            "price": 55000,
            "old_price": 79000,
            "sale": 30,
        }
        with patch("app.ui.pricing_tab.api_request") as get:
            get.return_value.json.return_value = [product]
            worker = PricingFetchThread("https://api.botocit.com/api/v2/telegram-buyer/products")
            received = []
            worker.result_ready.connect(lambda *args: received.append(args))
            worker.run()
        self.assertEqual(received, [(True, [product], "")])
        get.assert_called_once_with(
            "GET", worker.url, headers={"Accept": "application/json"}, timeout=10
        )

        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab.update_pricing_data(received[0][1])
        texts = [label.text() for label in tab.offers_container.findChildren(QLabel)]
        for expected in ("Google Pro 18 tháng", "Sale 30%", "79.000đ", "55.000đ"):
            self.assertIn(expected, texts)

    def test_empty_response_and_failed_request_show_status(self):
        with patch.object(PricingTab, "refresh_pricing"):
            tab = PricingTab()
        tab._on_pricing_loaded(True, [], "")
        self.assertIn("Chưa có sản phẩm", tab.lbl_status.text())
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

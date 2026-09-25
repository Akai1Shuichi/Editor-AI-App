import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel

from app.ui.pricing_tab import PricingTab, PricingFetchThread


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
        with patch("app.ui.pricing_tab.requests.get") as get:
            get.return_value.json.return_value = [product]
            worker = PricingFetchThread("https://api.botocit.com/api/v2/telegram-buyer/products")
            received = []
            worker.result_ready.connect(lambda *args: received.append(args))
            worker.run()
        self.assertEqual(received, [(True, [product], "")])
        get.assert_called_once_with(
            worker.url, headers={"Accept": "application/json"}, timeout=10
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


if __name__ == "__main__":
    unittest.main()

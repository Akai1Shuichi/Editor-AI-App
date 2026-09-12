import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from app.ui.pricing_tab import PricingTab, PricingFetchThread, format_vnd_price


class PricingTabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_format_vnd_price(self):
        self.assertEqual(format_vnd_price(65000), "65.000đ")
        self.assertEqual(format_vnd_price(92000), "92.000đ")
        self.assertEqual(format_vnd_price("65000"), "65.000đ")
        self.assertEqual(format_vnd_price("65.000đ"), "65.000đ")
        self.assertEqual(format_vnd_price(None), "")

    def test_update_pricing_data(self):
        with patch.object(PricingFetchThread, "start"):
            tab = PricingTab()

        tab.update_pricing_data({
            "sale": "30%",
            "price": 65000,
            "old_price": 92000,
        })

        self.assertEqual(tab.lbl_bot_offer_name.text(), "ElevenLabs Redeem 131K Credit · Sale 30%")
        self.assertEqual(tab.lbl_bot_offer_original_price.text(), "92.000đ")
        self.assertEqual(tab.lbl_bot_offer_sale_price.text(), "65.000đ")

    def test_pricing_fetch_thread_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "sale": "40%",
            "price": 55000,
            "old_price": 92000,
        }
        mock_resp.raise_for_status.return_value = None

        results = []
        thread = PricingFetchThread(url="http://test.url")
        thread.result_ready.connect(lambda ok, data, err: results.append((ok, data, err)))

        with patch("app.ui.pricing_tab.requests.get", return_value=mock_resp) as mock_get:
            thread.run()
            mock_get.assert_called_once()
            call_kwargs = mock_get.call_args.kwargs
            self.assertIn("params", call_kwargs)
            self.assertIn("t", call_kwargs["params"])
            self.assertIsInstance(call_kwargs["params"]["t"], int)

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0][0])
        self.assertEqual(results[0][1]["price"], 55000)
        self.assertEqual(results[0][1]["sale"], "40%")

    def test_pricing_fetch_thread_failure(self):
        results = []
        thread = PricingFetchThread(url="http://test.url")
        thread.result_ready.connect(lambda ok, data, err: results.append((ok, data, err)))

        with patch("app.ui.pricing_tab.requests.get", side_effect=Exception("Network error")):
            thread.run()

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0][0])
        self.assertIn("Network error", results[0][2])

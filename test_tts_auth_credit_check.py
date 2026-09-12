import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from app.ui.tts_tab import TTSTab, TTSWorker
from app.ui.main_window import MainWindow


class TTSAuthCreditCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_tts_worker_calls_auth_before_and_after_generation(self):
        """TTSWorker must call get_account_info to check auth before generating and after finishing."""
        worker = TTSWorker(
            text="Hello world",
            voice_id="voice-1",
            model_id="model-1",
            lang_code="vi",
            voice_settings={},
            export_srt=False,
            output_filename="test.mp3",
            output_dir=Path("/tmp"),
        )

        emitted_accounts = []
        worker.account_updated.connect(lambda info: emitted_accounts.append(info))

        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        # First call before generation returns 100 credits, second call after returns 80 credits
        mock_client.get_account_info.side_effect = [
            {"credit_balance": 100, "name": "Tester"},
            {"credit_balance": 80, "name": "Tester"},
        ]
        mock_client.generate_and_download.return_value = (
            Path("/tmp/test.mp3"),
            None,
        )

        with patch("app.ui.tts_tab.VibiClient", return_value=mock_client):
            worker.run()

        self.assertEqual(mock_client.get_account_info.call_count, 2)
        self.assertEqual(len(emitted_accounts), 2)
        self.assertEqual(emitted_accounts[0]["credit_balance"], 100)
        self.assertEqual(emitted_accounts[1]["credit_balance"], 80)

    def test_tts_worker_aborts_if_initial_auth_fails(self):
        """If auth check fails before generation, worker emits failure and does not generate."""
        worker = TTSWorker(
            text="Hello world",
            voice_id="voice-1",
            model_id="model-1",
            lang_code="vi",
            voice_settings={},
            export_srt=False,
        )

        finished_results = []
        worker.task_finished.connect(
            lambda success, audio, srt, msg: finished_results.append((success, msg))
        )

        mock_client = MagicMock()
        mock_client.is_configured.return_value = True
        mock_client.get_account_info.side_effect = Exception("401 Unauthorized")

        with patch("app.ui.tts_tab.VibiClient", return_value=mock_client):
            worker.run()

        self.assertEqual(len(finished_results), 1)
        self.assertFalse(finished_results[0][0])
        self.assertIn("401 Unauthorized", finished_results[0][1])
        mock_client.generate_and_download.assert_not_called()

    def test_tts_tab_updates_credit_balance_on_account_updated(self):
        """TTSTab updates credit balance and re-emits account_updated."""
        tab = TTSTab()
        received_infos = []
        tab.account_updated.connect(lambda info: received_infos.append(info))

        account_info = {"credit_balance": 54321, "name": "User A"}
        tab._on_account_updated(account_info)

        self.assertEqual(tab.credit_balance, 54321)
        self.assertEqual(len(received_infos), 1)
        self.assertEqual(received_infos[0]["credit_balance"], 54321)
        self.assertIn("54,321", tab.lbl_char_count.text())

    def test_main_window_syncs_credits_across_all_tabs(self):
        """MainWindow updates tts_tab, project_workspace.tts_tab, settings_tab, and api_chip."""
        with patch("app.ui.main_window.MainWindow.update_api_status_badge"):
            win = MainWindow()

        account_info = {"credit_balance": 88888, "name": "Alice", "email": "alice@test.com"}
        win.on_account_updated(account_info)

        self.assertEqual(win.tts_tab.credit_balance, 88888)
        self.assertEqual(win.project_workspace.tts_tab.credit_balance, 88888)
        self.assertIn("88,888", win.api_chip.text())
        self.assertIn("88,888", win.settings_tab.lbl_credits.text())
        self.assertIn("Alice", win.settings_tab.lbl_user.text())

    def test_srt_toggle_switch_and_label(self):
        """SRT export option uses a ToggleSwitch with '+15%' label on its own row."""
        tab = TTSTab()
        self.assertTrue(tab.chk_srt.isChecked())
        self.assertIn("Xuất file phụ đề SRT", tab.lbl_srt_text.text())
        self.assertIn("+15% credits", tab.lbl_srt_text.text())

        # Clicking label toggles switch
        tab.lbl_srt_text.mousePressEvent(None)
        self.assertFalse(tab.chk_srt.isChecked())
        tab.lbl_srt_text.mousePressEvent(None)
        self.assertTrue(tab.chk_srt.isChecked())

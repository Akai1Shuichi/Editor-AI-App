import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QFileDialog, QComboBox,
    QProgressBar
)

from app import config
from app.core.vibi_client import VibiClient, VibiAPIError

class AccountCheckThread(QThread):
    """Worker kiểm tra số dư và thông tin tài khoản Vibi."""
    result_ready = pyqtSignal(bool, dict, str)

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key

    def run(self):
        client = VibiClient(api_key=self.api_key)
        if not client.is_configured():
            self.result_ready.emit(False, {}, "Vui lòng nhập Voice API Key trước khi kiểm tra!")
            return

        try:
            info = client.get_account_info()
            self.result_ready.emit(True, info, "")
        except Exception as e:
            self.result_ready.emit(False, {}, str(e))


class SettingsTab(QWidget):
    """Tab quản lý API Key, kiểm tra số dư Credits và cấu hình hệ thống - Thiết kế gọn gàng, chuẩn form UX."""
    api_key_saved = pyqtSignal(str)
    account_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.worker: Optional[AccountCheckThread] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # 1. Panel Tài khoản & Vibi API Key
        acc_panel = QFrame()
        acc_panel.setProperty("class", "panel")
        acc_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        ap_layout = QVBoxLayout(acc_panel)
        ap_layout.setContentsMargins(14, 12, 14, 12)
        ap_layout.setSpacing(10)

        lbl_acc_header = QLabel("Tài Khoản Voice API")
        lbl_acc_header.setProperty("class", "panel_title")
        ap_layout.addWidget(lbl_acc_header)

        # Hàng nhập API Key
        key_row = QHBoxLayout()
        key_row.setSpacing(8)

        lbl_k = QLabel("Voice API Key:")
        lbl_k.setProperty("class", "section_label")
        lbl_k.setFixedWidth(90)

        self.edit_key = QLineEdit(config.VIBI_API_KEY)
        self.edit_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit_key.setPlaceholderText("Nhập Voice API Key...")

        self.btn_toggle_key = QPushButton("Hiện")
        self.btn_toggle_key.setFixedWidth(50)
        self.btn_toggle_key.setObjectName("btn_subtle")
        self.btn_toggle_key.clicked.connect(self.toggle_key_visibility)

        self.btn_save_key = QPushButton("Lưu")
        self.btn_save_key.setObjectName("btn_primary")
        self.btn_save_key.clicked.connect(self.save_api_key)

        self.btn_check = QPushButton("Kiểm Tra Số Dư")
        self.btn_check.clicked.connect(self.check_account)

        key_row.addWidget(lbl_k)
        key_row.addWidget(self.edit_key, stretch=2)
        key_row.addWidget(self.btn_toggle_key)
        key_row.addWidget(self.btn_save_key)
        key_row.addWidget(self.btn_check)
        ap_layout.addLayout(key_row)

        # Thông tin tài khoản (Dòng thẻ thông tin gọn gàng)
        self.info_box = QFrame()
        self.info_box.setStyleSheet("background-color: #14151b; border: 1px solid #23252d; border-radius: 6px; padding: 8px;")
        ib_layout = QHBoxLayout(self.info_box)

        self.lbl_credits = QLabel("Số dư: -- credits")
        self.lbl_credits.setStyleSheet("font-size: 14px; font-weight: 700; color: #10b981;")

        self.lbl_user = QLabel("Người dùng: --")
        self.lbl_user.setStyleSheet("color: #9ca3af; font-size: 12px;")

        self.lbl_email = QLabel("Email: --")
        self.lbl_email.setStyleSheet("color: #9ca3af; font-size: 12px;")

        ib_layout.addWidget(self.lbl_credits)
        ib_layout.addStretch()
        ib_layout.addWidget(self.lbl_user)
        ib_layout.addSpacing(15)
        ib_layout.addWidget(self.lbl_email)

        ap_layout.addWidget(self.info_box)
        layout.addWidget(acc_panel)

        # 2. Panel Cấu hình mặc định
        pref_panel = QFrame()
        pref_panel.setProperty("class", "panel")
        pref_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pp_layout = QVBoxLayout(pref_panel)
        pp_layout.setContentsMargins(14, 12, 14, 12)
        pp_layout.setSpacing(10)

        lbl_pref_header = QLabel("Cài Đặt Mặc Định")
        lbl_pref_header.setProperty("class", "panel_title")
        pp_layout.addWidget(lbl_pref_header)

        # Voice ID mặc định
        r1 = QHBoxLayout()
        lbl_def_v = QLabel("Voice ID mặc định:")
        lbl_def_v.setProperty("class", "section_label")
        lbl_def_v.setFixedWidth(140)
        self.edit_def_voice = QLineEdit(config.DEFAULT_VIBI_VOICE_ID)
        r1.addWidget(lbl_def_v)
        r1.addWidget(self.edit_def_voice)
        pp_layout.addLayout(r1)

        # Model & Language mặc định
        r2 = QHBoxLayout()
        lbl_def_m = QLabel("Model mặc định:")
        lbl_def_m.setProperty("class", "section_label")
        lbl_def_m.setFixedWidth(140)
        self.combo_def_model = QComboBox()
        self.combo_def_model.addItems(["eleven_v3", "eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"])
        self.combo_def_model.setCurrentText(config.DEFAULT_VIBI_MODEL)

        lbl_def_l = QLabel("Ngôn ngữ:")
        lbl_def_l.setProperty("class", "section_label")
        self.combo_def_lang = QComboBox()
        self.combo_def_lang.addItems(["vi", "en", "ja", "ko", "zh"])
        self.combo_def_lang.setCurrentText(config.DEFAULT_VIBI_LANGUAGE)

        r2.addWidget(lbl_def_m)
        r2.addWidget(self.combo_def_model, stretch=1)
        r2.addSpacing(15)
        r2.addWidget(lbl_def_l)
        r2.addWidget(self.combo_def_lang, stretch=1)
        pp_layout.addLayout(r2)

        # Thư mục lưu Downloads
        r3 = QHBoxLayout()
        lbl_dir = QLabel("Thư mục lưu file:")
        lbl_dir.setProperty("class", "section_label")
        lbl_dir.setFixedWidth(140)

        self.lbl_dir_path = QLabel(str(config.DOWNLOADS_DIR))
        self.lbl_dir_path.setStyleSheet("color: #60a5fa; font-size: 12px;")

        self.btn_change_dir = QPushButton("Thay đổi...")
        self.btn_change_dir.clicked.connect(self.change_downloads_dir)

        self.btn_open_dir = QPushButton("Mở")
        self.btn_open_dir.clicked.connect(self.open_downloads_dir)

        r3.addWidget(lbl_dir)
        r3.addWidget(self.lbl_dir_path, stretch=1)
        r3.addWidget(self.btn_change_dir)
        r3.addWidget(self.btn_open_dir)
        pp_layout.addLayout(r3)

        # Nút lưu cài đặt
        self.btn_save_all = QPushButton("Lưu Cài Đặt")
        self.btn_save_all.setObjectName("btn_primary")
        self.btn_save_all.clicked.connect(self.save_preferences)
        pp_layout.addWidget(self.btn_save_all)

        layout.addWidget(pref_panel)
        layout.addStretch()

        if config.VIBI_API_KEY:
            self.check_account()

    def toggle_key_visibility(self):
        if self.edit_key.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("Ẩn")
        else:
            self.edit_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("Hiện")

    def save_api_key(self):
        key = self.edit_key.text().strip()
        config.VIBI_API_KEY = key
        config.save_env_variable("VIBI_API_KEY", key)
        self.api_key_saved.emit(key)
        QMessageBox.information(self, "Đã lưu", "Đã lưu Voice API Key thành công!")
        if key:
            self.check_account()

    def check_account(self):
        key = self.edit_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Chưa có Key", "Vui lòng nhập Voice API Key!")
            return

        self.btn_check.setEnabled(False)
        self.lbl_credits.setText("Đang kiểm tra...")

        self.worker = AccountCheckThread(api_key=key)
        self.worker.result_ready.connect(self.on_account_checked)
        self.worker.start()

    def on_account_checked(self, success: bool, info: dict, error_msg: str):
        self.btn_check.setEnabled(True)

        if success:
            credits = info.get("credit_balance")
            if credits is None:
                credits = info.get("credits", 0)
            name = info.get("name") or "User"
            email = info.get("email") or "-"

            self.lbl_credits.setText(f"Số dư: {credits:,} credits")
            self.lbl_credits.setStyleSheet("font-size: 14px; font-weight: 700; color: #10b981;")
            self.lbl_user.setText(f"Người dùng: {name}")
            self.lbl_email.setText(f"Email: {email}")
            self.account_updated.emit(info)
        else:
            self.lbl_credits.setText("Không thể kết nối")
            self.lbl_credits.setStyleSheet("font-size: 13px; font-weight: 600; color: #f87171;")
            QMessageBox.critical(self, "Lỗi kiểm tra", error_msg)

    def change_downloads_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu Downloads", str(config.DOWNLOADS_DIR))
        if folder:
            p = Path(folder)
            config.DOWNLOADS_DIR = p
            self.lbl_dir_path.setText(str(p))

    def open_downloads_dir(self):
        target = config.DOWNLOADS_DIR
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target)])
            else:
                subprocess.run(["xdg-open", str(target)])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {e}")

    def save_preferences(self):
        def_voice = self.edit_def_voice.text().strip()
        def_model = self.combo_def_model.currentText()
        def_lang = self.combo_def_lang.currentText()

        if def_voice:
            config.save_env_variable("DEFAULT_VIBI_VOICE_ID", def_voice)
            config.DEFAULT_VIBI_VOICE_ID = def_voice
        if def_model:
            config.save_env_variable("DEFAULT_VIBI_MODEL", def_model)
            config.DEFAULT_VIBI_MODEL = def_model
        if def_lang:
            config.save_env_variable("DEFAULT_VIBI_LANGUAGE", def_lang)
            config.DEFAULT_VIBI_LANGUAGE = def_lang

        QMessageBox.information(self, "Đã lưu", "Đã lưu toàn bộ cài đặt mặc định!")

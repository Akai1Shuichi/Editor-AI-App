from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, QSize, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QMessageBox, QFileDialog
)

from app import config
from app.core.vibi_client import VibiClient
from app.core.platform_utils import open_path

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class AccountCheckThread(QThread):
    """Worker kiểm tra số dư và thông tin tài khoản Vibi."""
    result_ready = pyqtSignal(str, bool, dict, str)

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key

    def run(self):
        client = VibiClient(api_key=self.api_key)
        if not client.is_configured():
            self.result_ready.emit(
                self.api_key or "",
                False,
                {},
                "Vui lòng nhập Voice API Key trước khi kiểm tra!",
            )
            return

        try:
            info = client.get_account_info()
            self.result_ready.emit(self.api_key or "", True, info, "")
        except Exception as e:
            self.result_ready.emit(self.api_key or "", False, {}, str(e))


class SettingsTab(QWidget):
    """Tab quản lý API Key, kiểm tra số dư Credits và cấu hình hệ thống - Thiết kế gọn gàng, chuẩn form UX."""
    api_key_saved = pyqtSignal(str)
    account_updated = pyqtSignal(dict)
    request_pricing = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.worker: Optional[AccountCheckThread] = None
        self._pending_api_key: Optional[str] = None
        self._active_check_key: Optional[str] = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        page_title = QLabel("Cài đặt")
        page_title.setObjectName("page_heading")
        page_subtitle = QLabel(
            "Quản lý tài khoản Voice API và thư mục lưu dự án."
        )
        page_subtitle.setObjectName("page_subtitle")
        layout.addWidget(page_title)
        layout.addWidget(page_subtitle)

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

        self._eye_icon = QIcon(str(ICONS_DIR / "eye.svg"))
        self._eye_off_icon = QIcon(str(ICONS_DIR / "eye-off.svg"))
        self.btn_toggle_key = QPushButton()
        self.btn_toggle_key.setFixedSize(34, 34)
        self.btn_toggle_key.setIcon(self._eye_icon)
        self.btn_toggle_key.setIconSize(QSize(18, 18))
        self.btn_toggle_key.setToolTip("Hiện API Key")
        self.btn_toggle_key.setAccessibleName("Hiện API Key")
        self.btn_toggle_key.setObjectName("btn_subtle")
        self.btn_toggle_key.clicked.connect(self.toggle_key_visibility)

        self.btn_save_key = QPushButton("Lưu")
        self.btn_save_key.setObjectName("btn_primary")
        self.btn_save_key.clicked.connect(self.save_api_key)

        key_row.addWidget(lbl_k)
        key_row.addWidget(self.edit_key, stretch=2)
        key_row.addWidget(self.btn_toggle_key)
        key_row.addWidget(self.btn_save_key)
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

        self.lbl_vibi_test_key = QLabel(
            'Lấy API Key test tại đây: '
            '<a href="https://vibi.pro" '
            'style="color: #60a5fa; text-decoration: underline;">Vibi.pro</a>'
        )
        self.lbl_vibi_test_key.setOpenExternalLinks(True)
        self.lbl_vibi_test_key.setStyleSheet(
            "color: #dbeafe; background-color: #182235; "
            "border: 1px solid #2d5d94; border-radius: 6px; "
            "padding: 6px 9px; font-size: 12px; font-weight: 600;"
        )
        key_help_row = QHBoxLayout()
        key_help_row.setContentsMargins(0, 0, 0, 0)
        key_help_row.setSpacing(8)
        key_help_row.addWidget(self.lbl_vibi_test_key)
        key_help_row.addStretch()
        self.btn_buy_api_key = QPushButton("Mua API Key")
        self.btn_buy_api_key.setObjectName("btn_buy_api")
        self.btn_buy_api_key.setToolTip("Xem bảng giá Voice API")
        self.btn_buy_api_key.clicked.connect(self.request_pricing.emit)
        key_help_row.addWidget(self.btn_buy_api_key)
        ap_layout.addLayout(key_help_row)

        layout.addWidget(acc_panel)

        # 2. Panel thư mục dự án
        pref_panel = QFrame()
        pref_panel.setProperty("class", "panel")
        pref_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pp_layout = QVBoxLayout(pref_panel)
        pp_layout.setContentsMargins(14, 12, 14, 12)
        pp_layout.setSpacing(10)

        lbl_pref_header = QLabel("Thư Mục Dự Án")
        lbl_pref_header.setProperty("class", "panel_title")
        pp_layout.addWidget(lbl_pref_header)

        # Đường dẫn lưu Projects
        project_dir_row = QHBoxLayout()
        lbl_dir = QLabel("Đường dẫn lưu Projects:")
        lbl_dir.setProperty("class", "section_label")
        lbl_dir.setFixedWidth(160)

        self.lbl_dir_path = QLabel(str(config.PROJECTS_DIR))
        self.lbl_dir_path.setStyleSheet("color: #60a5fa; font-size: 12px;")

        self.btn_change_dir = QPushButton("Thay đổi...")
        self.btn_change_dir.clicked.connect(self.change_projects_dir)

        self.btn_open_dir = QPushButton("Mở")
        self.btn_open_dir.clicked.connect(self.open_projects_dir)

        project_dir_row.addWidget(lbl_dir)
        project_dir_row.addWidget(self.lbl_dir_path, stretch=1)
        project_dir_row.addWidget(self.btn_change_dir)
        project_dir_row.addWidget(self.btn_open_dir)
        pp_layout.addLayout(project_dir_row)

        layout.addWidget(pref_panel)
        layout.addStretch()

        if config.VIBI_API_KEY:
            self.check_account()

    def toggle_key_visibility(self):
        if self.edit_key.echoMode() == QLineEdit.EchoMode.Password:
            self.edit_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setIcon(self._eye_off_icon)
            self.btn_toggle_key.setToolTip("Ẩn API Key")
            self.btn_toggle_key.setAccessibleName("Ẩn API Key")
        else:
            self.edit_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setIcon(self._eye_icon)
            self.btn_toggle_key.setToolTip("Hiện API Key")
            self.btn_toggle_key.setAccessibleName("Hiện API Key")

    def save_api_key(self):
        key = self.edit_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Chưa có Key", "Vui lòng nhập Voice API Key!")
            return

        self._pending_api_key = key
        self._start_account_check(key)

    def check_account(self):
        key = self.edit_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Chưa có Key", "Vui lòng nhập Voice API Key!")
            return

        self._pending_api_key = None
        self._start_account_check(key)

    def _start_account_check(self, key: str):
        self._active_check_key = key
        self.btn_save_key.setEnabled(False)
        self.lbl_credits.setText("Đang kiểm tra...")

        self.worker = AccountCheckThread(api_key=key)
        self.worker.result_ready.connect(self.on_account_checked)
        self.worker.start()

    def on_account_checked(self, checked_key: str, success: bool, info: dict, error_msg: str):
        if checked_key != self._active_check_key:
            return

        self._active_check_key = None
        self.btn_save_key.setEnabled(True)
        pending_api_key = self._pending_api_key

        if success:
            if pending_api_key == checked_key:
                config.save_setting("VIBI_API_KEY", pending_api_key)
                config.VIBI_API_KEY = pending_api_key
                self.api_key_saved.emit(pending_api_key)
                QMessageBox.information(
                    self,
                    "Đã lưu",
                    "Đã kiểm tra và lưu Voice API Key thành công!",
                )
                self._pending_api_key = None

            self.update_account_info(info)
            self.account_updated.emit(info)
        else:
            if pending_api_key == checked_key:
                self._pending_api_key = None
            self.lbl_credits.setText("Không thể kết nối")
            self.lbl_credits.setStyleSheet("font-size: 13px; font-weight: 600; color: #f87171;")
            QMessageBox.critical(self, "Lỗi kiểm tra", error_msg)

    def update_account_info(self, info: dict):
        """Cập nhật hiển thị thông tin tài khoản và số dư credits trên giao diện Settings."""
        credits = info.get("credit_balance")
        if credits is None:
            credits = info.get("credits", 0)
        name = info.get("name") or "User"
        email = info.get("email") or "-"

        self.lbl_credits.setText(f"Số dư: {credits:,} credits")
        self.lbl_credits.setStyleSheet("font-size: 14px; font-weight: 700; color: #10b981;")
        self.lbl_user.setText(f"Người dùng: {name}")
        self.lbl_email.setText(f"Email: {email}")

    def change_projects_dir(self):
        """Cho phép user chọn thư mục lưu projects mới."""
        folder = QFileDialog.getExistingDirectory(
            self, "Chọn đường dẫn lưu Projects", str(config.PROJECTS_DIR)
        )
        if folder:
            p = Path(folder)
            p.mkdir(parents=True, exist_ok=True)
            config.PROJECTS_DIR = p
            config.save_setting("PROJECTS_DIR", str(p))
            self.lbl_dir_path.setText(str(p))

    def open_projects_dir(self):
        """Mở thư mục chứa projects trong File Explorer."""
        target = config.PROJECTS_DIR
        try:
            open_path(target)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {e}")

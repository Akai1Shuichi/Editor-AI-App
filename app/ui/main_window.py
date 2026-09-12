from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame
)

from app import config
from app.core.standalone_state import StandaloneStateStore
from app.ui.project_workspace import ProjectWorkspace
from app.ui.watermark_tab import WatermarkTab
from app.ui.tts_tab import TTSTab
from app.ui.settings_tab import SettingsTab
from app.ui.pricing_tab import PricingTab

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng - Giao diện Studio tối giản, trực quan, chuẩn UI/UX."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Editor AI App v 1.0")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self.nav_buttons = []
        self.standalone_state = StandaloneStateStore()
        self.init_ui()
        self.update_api_status_badge()

    def init_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        # ================= SIDEBAR =================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(4)

        # Navigation Buttons (Điều hướng các module chính)
        self.btn_nav_project = self.create_nav_btn("📁  Dự án", 0)
        self.btn_nav_watermark = self.create_nav_btn("🍌  Gỡ watermark Google Flow", 1)
        self.btn_nav_tts = self.create_nav_btn("🎙  Tạo Voice TTS", 2)
        self.btn_nav_settings = self.create_nav_btn("⚙  Cài đặt", 3)
        self.btn_nav_pricing = self.create_nav_btn("🏷  Bảng giá", 4)

        sb_layout.addWidget(self.btn_nav_project)
        sb_layout.addWidget(self.btn_nav_watermark)
        sb_layout.addWidget(self.btn_nav_tts)
        sb_layout.addWidget(self.btn_nav_settings)
        sb_layout.addWidget(self.btn_nav_pricing)
        sb_layout.addStretch()

        # Sidebar Footer: Chứa badge Voice API và số dư Credits
        self.sidebar_footer = QWidget()
        self.sidebar_footer.setObjectName("sidebar_footer")
        f_layout = QVBoxLayout(self.sidebar_footer)
        f_layout.setContentsMargins(12, 12, 12, 12)
        f_layout.setSpacing(0)

        self.api_chip = QLabel("Chưa cấu hình API")
        self.api_chip.setObjectName("api_chip")
        self.api_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_layout.addWidget(self.api_chip)

        sb_layout.addWidget(self.sidebar_footer)
        workspace_layout.addWidget(sidebar)

        # ================= CONTENT AREA =================
        content_container = QWidget()
        content_container.setObjectName("content_container")
        content_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Stacked Pages:
        # Index 0: ProjectWorkspace (Bao gồm Quản lý dự án + quy trình dự án)
        # Index 1: WatermarkTab (Công cụ gỡ watermark độc lập)
        # Index 2: TTSTab (Công cụ tạo giọng nói TTS độc lập)
        # Index 3: SettingsTab (Cấu hình Voice API & tài khoản)
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_container")
        self.stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.project_workspace = ProjectWorkspace()
        self.watermark_tab = WatermarkTab()
        self.tts_tab = TTSTab()
        self.settings_tab = SettingsTab()
        self.pricing_tab = PricingTab()

        self.watermark_tab.configure_standalone(
            self.standalone_state, config.WATERMARK_DOWNLOADS_DIR
        )
        self.tts_tab.configure_standalone(
            self.standalone_state, config.TTS_DOWNLOADS_DIR
        )

        self.stack.addWidget(self.project_workspace)
        self.stack.addWidget(self.watermark_tab)
        self.stack.addWidget(self.tts_tab)
        self.stack.addWidget(self.settings_tab)
        self.stack.addWidget(self.pricing_tab)

        content_layout.addWidget(self.stack)
        workspace_layout.addWidget(content_container)
        root_layout.addLayout(workspace_layout, stretch=1)

        self.app_footer = QFrame()
        self.app_footer.setObjectName("app_footer")
        self.app_footer.setMinimumHeight(60)
        footer_layout = QHBoxLayout(self.app_footer)
        footer_layout.setContentsMargins(24, 10, 24, 10)
        footer_layout.setSpacing(14)

        self.footer_support = QWidget(self.app_footer)
        support_layout = QHBoxLayout(self.footer_support)
        support_layout.setContentsMargins(0, 0, 0, 0)
        support_layout.setSpacing(6)

        self.lbl_footer_telegram_icon = QLabel()
        self.lbl_footer_telegram_icon.setPixmap(
            QPixmap(str(ICONS_DIR / "telegram.svg")).scaled(
                20, 20, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.lbl_footer_telegram = QLabel(
            'Shop AI: '
            '<a href="https://t.me/DichVuIT_bot" '
            'style="color: #93c5fd; text-decoration: underline;">@DichVuIT_bot</a>'
        )
        self.lbl_footer_telegram.setOpenExternalLinks(True)
        self.lbl_footer_telegram.setStyleSheet("color: #dbeafe; font-size: 12px; font-weight: 600;")

        self.lbl_footer_zalo_icon = QLabel()
        self.lbl_footer_zalo_icon.setPixmap(
            QPixmap(str(ICONS_DIR / "zalo.svg")).scaled(
                20, 20, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.lbl_footer_zalo = QLabel(
            '<a href="https://zalo.me/g/2h4r4fbobrg66e9haa3q" '
            'style="color: #93c5fd; text-decoration: underline;">Hỗ trợ tại Zalo</a>'
        )
        self.lbl_footer_zalo.setOpenExternalLinks(True)
        self.lbl_footer_zalo.setStyleSheet("color: #dbeafe; font-size: 12px; font-weight: 600;")

        support_layout.addWidget(self.lbl_footer_telegram_icon)
        support_layout.addWidget(self.lbl_footer_telegram)
        support_layout.addSpacing(18)
        support_layout.addWidget(self.lbl_footer_zalo_icon)
        support_layout.addWidget(self.lbl_footer_zalo)
        footer_layout.addWidget(self.footer_support)
        footer_layout.addStretch()

        self.footer_creator = QLabel("© Created by: trtoan")
        self.footer_creator.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        footer_layout.addWidget(self.footer_creator)

        root_layout.addWidget(self.app_footer)

        # Inter-tab Connections
        self.settings_tab.api_key_saved.connect(self.on_api_key_saved)
        self.settings_tab.account_updated.connect(self.on_account_updated)
        self.settings_tab.request_pricing.connect(lambda: self.switch_page(4))
        self.tts_tab.account_updated.connect(self.on_account_updated)
        self.project_workspace.tts_tab.account_updated.connect(self.on_account_updated)
        self.switch_page(self.standalone_state.load_last_page())

    def create_nav_btn(self, title: str, index: int) -> QPushButton:
        btn = QPushButton(title)
        btn.setObjectName("nav_btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda _, idx=index: self.switch_page(idx))
        self.nav_buttons.append(btn)
        return btn

    def switch_page(self, index: int):
        prev_index = self.stack.currentIndex()
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.standalone_state.save_last_page(index)
        if index == 0:
            if prev_index == 0 and self.project_workspace.current_project:
                self.project_workspace.show_project_list()
            elif not self.project_workspace.current_project:
                self.project_workspace.show_project_list()

    def on_api_key_saved(self, key: str):
        self.update_api_status_badge()

    def on_account_updated(self, info: dict):
        credits = info.get("credit_balance")
        if credits is None:
            credits = info.get("credits", 0)
        self.tts_tab.set_credit_balance(credits)
        self.project_workspace.tts_tab.set_credit_balance(credits)
        self.settings_tab.update_account_info(info)
        self.api_chip.setText(f"● Voice API: {credits:,} credits")
        self.api_chip.setStyleSheet("background-color: #064e3b; border: 1px solid #065f46; color: #34d399; border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: 600;")

    def update_api_status_badge(self):
        if config.VIBI_API_KEY and len(config.VIBI_API_KEY.strip()) > 0:
            self.api_chip.setText("Voice API\nĐã cấu hình")
            self.api_chip.setStyleSheet("color: #a7afbe; padding: 6px 10px; font-size: 11px;")
        else:
            self.api_chip.setText("Voice API\nChưa cấu hình")
            self.api_chip.setStyleSheet("color: #70798a; padding: 6px 10px; font-size: 11px;")

    def closeEvent(self, event):
        self.tts_tab.flush_standalone_state()
        super().closeEvent(event)

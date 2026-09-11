from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame
)

from app import config
from app.ui.watermark_tab import WatermarkTab
from app.ui.tts_tab import TTSTab
from app.ui.settings_tab import SettingsTab

class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng - Giao diện tối giản, trực quan, chuẩn UI/UX."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Media Studio")
        self.resize(1120, 720)
        self.setMinimumSize(920, 600)

        self.nav_buttons = []
        self.init_ui()
        self.update_api_status_badge()

    def init_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ================= SIDEBAR =================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(2)

        # Sidebar Brand
        brand_box = QWidget()
        brand_box.setObjectName("sidebar_brand")
        b_layout = QVBoxLayout(brand_box)
        b_layout.setContentsMargins(16, 16, 16, 10)
        b_layout.setSpacing(2)

        logo = QLabel("Studio AI")
        logo.setObjectName("app_logo")
        tagline = QLabel("Watermark & Voice Studio")
        tagline.setObjectName("app_tagline")

        b_layout.addWidget(logo)
        b_layout.addWidget(tagline)
        sb_layout.addWidget(brand_box)

        # Navigation Buttons
        self.btn_nav_watermark = self.create_nav_btn("🧹  Gỡ Watermark", 0)
        self.btn_nav_tts = self.create_nav_btn("🎙️  Tạo giọng TTS", 1)
        self.btn_nav_settings = self.create_nav_btn("⚙️  Cài đặt && Số dư", 2)

        sb_layout.addWidget(self.btn_nav_watermark)
        sb_layout.addWidget(self.btn_nav_tts)
        sb_layout.addWidget(self.btn_nav_settings)
        sb_layout.addStretch()

        # Sidebar Footer: Chứa badge Voice API và số dư Credits
        footer = QWidget()
        footer.setObjectName("sidebar_footer")
        f_layout = QVBoxLayout(footer)
        f_layout.setContentsMargins(12, 12, 12, 12)
        f_layout.setSpacing(0)

        self.api_chip = QLabel("Chưa cấu hình API")
        self.api_chip.setObjectName("api_chip")
        self.api_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        f_layout.addWidget(self.api_chip)

        sb_layout.addWidget(footer)
        root_layout.addWidget(sidebar)

        # ================= CONTENT AREA =================
        content_container = QWidget()
        content_container.setObjectName("content_container")
        content_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(20, 8, 20, 8)

        self.lbl_page_title = QLabel("Gỡ Watermark AI")
        self.lbl_page_title.setObjectName("page_title")
        top_layout.addWidget(self.lbl_page_title)
        top_layout.addStretch()

        content_layout.addWidget(top_bar)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_container")
        self.stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.watermark_tab = WatermarkTab()
        self.tts_tab = TTSTab()
        self.settings_tab = SettingsTab()

        self.stack.addWidget(self.watermark_tab)
        self.stack.addWidget(self.tts_tab)
        self.stack.addWidget(self.settings_tab)

        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_container)

        # Inter-tab Connections
        self.settings_tab.api_key_saved.connect(self.on_api_key_saved)
        self.settings_tab.account_updated.connect(self.on_account_updated)

        self.switch_page(0)

    def create_nav_btn(self, title: str, index: int) -> QPushButton:
        btn = QPushButton(title)
        btn.setObjectName("nav_btn")
        btn.setCheckable(True)
        btn.clicked.connect(lambda: self.switch_page(index))
        self.nav_buttons.append(btn)
        return btn

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        titles = [
            "Gỡ Watermark Gemini / Imagen",
            "Tạo Giọng Nói Đa Nền Tảng (ElevenLabs, MiniMax, CapCut) & Thư Viện Voice",
            "Cài Đặt & Quản Lý Tài Khoản Voice API"
        ]
        if 0 <= index < len(titles):
            self.lbl_page_title.setText(titles[index])

    def on_api_key_saved(self, key: str):
        self.update_api_status_badge()

    def on_account_updated(self, info: dict):
        credits = info.get("credit_balance")
        if credits is None:
            credits = info.get("credits", 0)
        self.api_chip.setText(f"● Voice API: {credits:,} credits")
        self.api_chip.setStyleSheet("background-color: #064e3b; border: 1px solid #065f46; color: #34d399; border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: 600;")

    def update_api_status_badge(self):
        if config.VIBI_API_KEY and len(config.VIBI_API_KEY.strip()) > 0:
            self.api_chip.setText("● Voice API Đã Kết Nối")
            self.api_chip.setStyleSheet("background-color: #064e3b; border: 1px solid #065f46; color: #34d399; border-radius: 6px; padding: 6px 10px; font-size: 11px; font-weight: 600;")
        else:
            self.api_chip.setText("○ Chưa có Voice API Key")
            self.api_chip.setStyleSheet("background-color: #1a202c; border: 1px solid #2d3748; color: #94a3b8; border-radius: 6px; padding: 6px 10px; font-size: 11px;")

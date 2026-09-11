from PyQt6.QtCore import Qt
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


class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng - Giao diện Studio tối giản, trực quan, chuẩn UI/UX."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Media Studio")
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

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ================= SIDEBAR =================
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(4)

        # Sidebar Brand
        brand_box = QWidget()
        brand_box.setObjectName("sidebar_brand")
        b_layout = QVBoxLayout(brand_box)
        b_layout.setContentsMargins(16, 16, 16, 12)
        b_layout.setSpacing(2)

        logo = QLabel("AI MEDIA STUDIO")
        logo.setObjectName("app_logo")
        tagline = QLabel("Production workspace")
        tagline.setObjectName("app_tagline")

        b_layout.addWidget(logo)
        b_layout.addWidget(tagline)
        sb_layout.addWidget(brand_box)

        # Navigation Buttons (Điều hướng các module chính)
        self.btn_nav_project = self.create_nav_btn("Dự án", 0)
        self.btn_nav_watermark = self.create_nav_btn("Gỡ watermark Google Flow", 1)
        self.btn_nav_tts = self.create_nav_btn("Tạo Voice TTS", 2)
        self.btn_nav_settings = self.create_nav_btn("Cài đặt", 3)

        sb_layout.addWidget(self.btn_nav_project)
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

        content_layout.addWidget(self.stack)
        root_layout.addWidget(content_container)

        # Inter-tab Connections
        self.settings_tab.api_key_saved.connect(self.on_api_key_saved)
        self.settings_tab.account_updated.connect(self.on_account_updated)
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

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame
)

from app import config
from app.ui.project_workspace import ProjectWorkspace
from app.ui.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Cửa sổ chính của ứng dụng - Giao diện Studio tối giản, trực quan, chuẩn UI/UX."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Media Studio")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

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

        # Navigation Buttons (Chuẩn Studio: Toàn bộ quy trình gỡ watermark, tạo voice, ghép video ở trong Màn Dự Án)
        self.btn_nav_project = self.create_nav_btn("Dự án", 0)
        self.btn_nav_settings = self.create_nav_btn("Cài đặt", 1)

        sb_layout.addWidget(self.btn_nav_project)
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
        # Index 0: ProjectWorkspace (Bao gồm Quản lý dự án + 3 bước: Watermark -> Voice TTS -> Ghép Video)
        # Index 1: SettingsTab (Cấu hình Voice API & tài khoản)
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_container")
        self.stack.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.project_workspace = ProjectWorkspace()
        self.settings_tab = SettingsTab()

        self.stack.addWidget(self.project_workspace)
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
        if index == 0:
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

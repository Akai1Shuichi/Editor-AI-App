from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.core.standalone_state import StandaloneStateStore
from app.ui.pricing_tab import PricingTab
from app.ui.watermark_tab import WatermarkTab
from app.ui.video_watermark_tab import VideoWatermarkTab
from app.version import APP_VERSION


ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class MainWindow(QMainWindow):
    """Cửa sổ công cụ gỡ watermark và Shop AI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Editor Video AI v{APP_VERSION}")
        self.resize(1240, 820)
        self.setMinimumSize(900, 640)

        self.nav_buttons: list[QPushButton] = []
        self.standalone_state = StandaloneStateStore()
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_title_bar())
        workspace_layout = QHBoxLayout()
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self._build_sidebar())

        self.watermark_pages = QTabWidget()
        self.watermark_pages.setObjectName("workspace_pages")
        self.watermark_tab = WatermarkTab()
        self.watermark_tab.configure_standalone(
            self.standalone_state, config.WATERMARK_DOWNLOADS_DIR
        )
        self.video_watermark_tab = VideoWatermarkTab()
        self.watermark_pages.addTab(self.watermark_tab, "Gỡ watermark Ảnh")
        self.watermark_pages.addTab(self.video_watermark_tab, "Gỡ watermark Video")
        self.watermark_pages.currentChanged.connect(self._on_watermark_tab_changed)
        self.pricing_tab = PricingTab()
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_container")
        self.stack.addWidget(self.watermark_pages)
        self.stack.addWidget(self.pricing_tab)
        workspace_layout.addWidget(self.stack, stretch=1)
        root_layout.addLayout(workspace_layout, stretch=1)
        root_layout.addWidget(self._build_footer())
        last_page = self.standalone_state.load_last_page()
        self.switch_page(last_page if last_page < self.stack.count() else 0)

    def _on_watermark_tab_changed(self, index: int) -> None:
        if self.watermark_pages.widget(index) is self.video_watermark_tab:
            self.video_watermark_tab.on_tab_activated()

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(4)

        self.btn_nav_watermark = self.create_nav_btn("🍌  Gỡ watermark", 0)
        self.btn_nav_pricing = self.create_nav_btn("🏷  Shop AI", 1)
        for button in self.nav_buttons:
            layout.addWidget(button)
        layout.addStretch()

        sidebar_footer = QWidget()
        sidebar_footer.setObjectName("sidebar_footer")
        layout.addWidget(sidebar_footer)
        return sidebar

    def create_nav_btn(self, title: str, index: int) -> QPushButton:
        button = QPushButton(title)
        button.setObjectName("nav_btn")
        button.setCheckable(True)
        button.clicked.connect(lambda _, page=index: self.switch_page(page))
        self.nav_buttons.append(button)
        return button

    def switch_page(self, index: int) -> None:
        if not 0 <= index < self.stack.count():
            return
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
        self.standalone_state.save_last_page(index)

    def _build_title_bar(self) -> QFrame:
        update_bar = QFrame()
        update_bar.setObjectName("update_bar")
        update_bar.setMinimumHeight(52)
        layout = QHBoxLayout(update_bar)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(10)

        title = QLabel("Editor Video AI")
        title.setStyleSheet("font-size: 14px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)
        layout.addStretch()

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        layout.addWidget(version_label)
        return update_bar

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("app_footer")
        footer.setMinimumHeight(54)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(6)

        zalo_icon = QLabel()
        zalo_icon.setPixmap(
            QPixmap(str(ICONS_DIR / "zalo.svg")).scaled(
                20, 20, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(zalo_icon)
        zalo_link = QLabel(
            '<a href="https://zalo.me/g/2h4r4fbobrg66e9haa3q" '
            'style="color: #93c5fd; text-decoration: underline;">Nhóm Zalo</a>'
        )
        zalo_link.setOpenExternalLinks(True)
        zalo_link.setStyleSheet("color: #93c5fd; font-size: 12px; font-weight: 600;")
        layout.addWidget(zalo_link)

        layout.addStretch()
        website_icon = QLabel()
        website_icon.setObjectName("footer_website_icon")
        website_icon.setPixmap(
            QPixmap(str(ICONS_DIR / "globe.svg")).scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(website_icon)
        website_link = QLabel(
            '<a href="https://botocit.com" '
            'style="color: #dbeafe; text-decoration: none;">botocit.com</a>'
        )
        website_link.setObjectName("footer_website_link")
        website_link.setOpenExternalLinks(True)
        website_link.setStyleSheet("font-size: 12px; font-weight: 700;")
        layout.addWidget(website_link)

        layout.addSpacing(16)
        donate_link = QLabel(
            '<a href="https://qr-donate.vercel.app/" '
            'style="color: #fbbf24; text-decoration: none;">'
            '<span style="color: #fb7185; font-size: 15px;">♥</span> '
            'Donate</a>'
        )
        donate_link.setObjectName("footer_donate_link")
        donate_link.setOpenExternalLinks(True)
        donate_link.setToolTip("Mở trang ủng hộ dự án")
        donate_link.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(donate_link)

        layout.addSpacing(16)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("color: #334155;")
        layout.addWidget(divider)
        layout.addSpacing(10)

        self.footer_creator = QLabel("© Created by: botocIT")
        self.footer_creator.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.footer_creator)
        return footer

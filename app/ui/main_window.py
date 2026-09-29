from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.core.standalone_state import StandaloneStateStore
from app.update_check import UpdateCheckerThread
from app.ui.pricing_tab import PricingTab
from app.ui.project_workspace import ProjectWorkspace
from app.ui.settings_tab import SettingsTab
from app.ui.tts_tab import TTSTab
from app.ui.watermark_tab import WatermarkTab
from app.ui.video_watermark_tab import VideoWatermarkTab
from app.version import APP_VERSION


ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
LATEST_RELEASE_URL = "https://github.com/Akai1Shuichi/Editor-AI-App/releases/latest"


class MainWindow(QMainWindow):
    """Cửa sổ chính của các công cụ và không gian dự án."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Editor Video AI v{APP_VERSION}")
        self.resize(1240, 820)
        self.setMinimumSize(900, 640)

        self.nav_buttons: list[QPushButton] = []
        self.standalone_state = StandaloneStateStore()
        self.init_ui()
        self.update_api_status_badge()
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._check_update_automatically)
        self._update_timer.start(1500)

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
        self.project_workspace = ProjectWorkspace()
        self.tts_tab = TTSTab()
        self.tts_tab.configure_standalone(
            self.standalone_state, config.TTS_DOWNLOADS_DIR
        )
        self.settings_tab = SettingsTab()
        self.pricing_tab = PricingTab()
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_container")
        self.stack.addWidget(self.project_workspace)
        self.stack.addWidget(self.watermark_pages)
        self.stack.addWidget(self.tts_tab)
        self.stack.addWidget(self.settings_tab)
        self.stack.addWidget(self.pricing_tab)
        self.settings_tab.request_pricing.connect(lambda: self.switch_page(4))
        self.settings_tab.api_key_saved.connect(self.update_api_status_badge)
        self.settings_tab.account_updated.connect(self.on_account_updated)
        self.tts_tab.account_updated.connect(self.on_account_updated)
        self.project_workspace.tts_tab.account_updated.connect(self.on_account_updated)
        workspace_layout.addWidget(self.stack, stretch=1)
        root_layout.addLayout(workspace_layout, stretch=1)
        root_layout.addWidget(self._build_footer())
        last_page = self.standalone_state.load_last_page()
        self.switch_page(last_page if last_page < self.stack.count() else 0)

    def _on_watermark_tab_changed(self, index: int) -> None:
        if self.watermark_pages.widget(index) is self.video_watermark_tab:
            self.video_watermark_tab.on_tab_activated()

    def on_account_updated(self, info: dict) -> None:
        credits = info.get("credit_balance", info.get("credits", 0))
        self.tts_tab.set_credit_balance(credits)
        self.project_workspace.tts_tab.set_credit_balance(credits)
        self.settings_tab.update_account_info(info)
        self.api_chip.setText(f"● Voice API: {credits:,} credits")
        self.api_chip.setStyleSheet(
            "background-color: #064e3b; border: 1px solid #065f46; "
            "border-radius: 6px; padding: 4px 10px; color: #34d399; "
            "font-size: 11px; font-weight: 600;"
            if credits > 0 else ""
        )

    def update_api_status_badge(self, *_args) -> None:
        self.api_chip.setStyleSheet("")
        self.api_chip.setText(
            "Voice API\nĐã cấu hình" if config.VIBI_API_KEY.strip()
            else "Voice API\nChưa cấu hình"
        )

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(4)

        self.btn_nav_project = self.create_nav_btn("📁  Dự án", 0)
        self.btn_nav_watermark = self.create_nav_btn("🍌  Gỡ watermark", 1)
        self.btn_nav_tts = self.create_nav_btn("🎙  Tạo Voice TTS", 2)
        self.btn_nav_settings = self.create_nav_btn("⚙  Cài đặt", 3)
        self.btn_nav_pricing = self.create_nav_btn("🏷  Shop AI", 4)
        for button in self.nav_buttons:
            layout.addWidget(button)
        layout.addStretch()

        sidebar_footer = QWidget()
        sidebar_footer.setObjectName("sidebar_footer")
        footer_layout = QVBoxLayout(sidebar_footer)
        footer_layout.setContentsMargins(12, 12, 12, 12)
        self.api_chip = QLabel()
        self.api_chip.setObjectName("api_chip")
        self.api_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(self.api_chip)
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
        previous_index = self.stack.currentIndex()
        self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)
        self.standalone_state.save_last_page(index)
        if index == 0 and (previous_index == 0 or not self.project_workspace.current_project):
            self.project_workspace.show_project_list()

    def closeEvent(self, event) -> None:
        self.tts_tab.flush_standalone_state()
        super().closeEvent(event)

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

        self.update_status_label = QLabel(f"v{APP_VERSION}  •  Chưa kiểm tra")
        self.update_status_label.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.update_status_label)
        self.update_button = QPushButton("Kiểm tra cập nhật")
        self.update_button.setObjectName("btn_subtle")
        self.update_button.clicked.connect(self._check_update_manually)
        layout.addWidget(self.update_button)
        return update_bar

    def _check_update_automatically(self) -> None:
        self._start_update_check(manual=False)

    def _check_update_manually(self) -> None:
        self._start_update_check(manual=True)

    def _start_update_check(self, *, manual: bool) -> None:
        if getattr(self, "_update_checker", None) and self._update_checker.isRunning():
            return
        self.update_button.setEnabled(False)
        self.update_status_label.setText("Đang kiểm tra cập nhật…")
        self._update_checker = UpdateCheckerThread(self)
        self._update_checker.update_available.connect(self._on_update_available)
        self._update_checker.no_update.connect(lambda: self._on_no_update(manual))
        self._update_checker.check_failed.connect(lambda message: self._on_update_check_failed(message, manual))
        self._update_checker.finished.connect(lambda: self.update_button.setEnabled(True))
        self._update_checker.start()

    def _on_update_available(self, update_info: dict) -> None:
        self.update_status_label.setText(f"↑ Có bản mới v{update_info['version']}")
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Có bản cập nhật mới")
        dialog.setTextFormat(Qt.TextFormat.RichText)
        dialog.setText(
            f"<p>Đã có phiên bản {escape(str(update_info['version']))}.</p>"
            f"{update_info['notes']}"
            f"<p>Link tải: {escape(LATEST_RELEASE_URL)}</p>"
        )
        download_button = dialog.addButton("Tải bản cập nhật", QMessageBox.ButtonRole.AcceptRole)
        dialog.addButton("Để sau", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        if dialog.clickedButton() is download_button:
            QDesktopServices.openUrl(QUrl(LATEST_RELEASE_URL))

    def _on_no_update(self, manual: bool) -> None:
        self.update_status_label.setText(f"✓ Đã cập nhật (v{APP_VERSION})")
        if manual:
            QMessageBox.information(self, "Kiểm tra cập nhật", "Bạn đang sử dụng phiên bản mới nhất.")

    def _on_update_check_failed(self, message: str, manual: bool) -> None:
        self.update_status_label.setText("Không thể kiểm tra cập nhật")
        if manual:
            QMessageBox.warning(self, "Kiểm tra cập nhật", f"Không thể kiểm tra bản cập nhật: {message}")

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

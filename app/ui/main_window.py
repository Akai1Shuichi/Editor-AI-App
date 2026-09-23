from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.core.standalone_state import StandaloneStateStore
from app.core.telemetry import TelemetryThread
from app.ui.watermark_tab import WatermarkTab
from app.ui.video_watermark_tab import VideoWatermarkTab
from app.updater import APP_VERSION, UpdateCheckerThread, UpdateDialog


ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class MainWindow(QMainWindow):
    """Giai đoạn 1: ứng dụng chỉ cung cấp công cụ gỡ watermark."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Editor Video AI v{APP_VERSION}")
        self.resize(1240, 820)
        self.setMinimumSize(900, 640)

        self.standalone_state = StandaloneStateStore()
        self.available_update_info: dict | None = None
        self.init_ui()
        QTimer.singleShot(0, self._record_installation)
        QTimer.singleShot(1500, self._check_update_automatically)

    def _record_installation(self) -> None:
        self._installation_telemetry = TelemetryThread("installation", self)
        self._installation_telemetry.start()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central_widget")
        central_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_update_bar())
        self.watermark_pages = QTabWidget()
        self.watermark_tab = WatermarkTab()
        self.watermark_tab.configure_standalone(
            self.standalone_state, config.WATERMARK_DOWNLOADS_DIR
        )
        self.video_watermark_tab = VideoWatermarkTab()
        self.watermark_pages.addTab(self.watermark_tab, "Gỡ watermark Ảnh")
        self.watermark_pages.addTab(self.video_watermark_tab, "Gỡ watermark Video")
        root_layout.addWidget(self.watermark_pages, stretch=1)
        root_layout.addWidget(self._build_footer())

    def _build_update_bar(self) -> QFrame:
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
        self.install_update_button = QPushButton("Cập nhật ngay")
        self.install_update_button.setObjectName("btn_primary")
        self.install_update_button.setVisible(False)
        self.install_update_button.clicked.connect(self._open_available_update)
        layout.addWidget(self.install_update_button)
        self.update_button = QPushButton("Kiểm tra cập nhật")
        self.update_button.setObjectName("btn_subtle")
        self.update_button.setToolTip("Kiểm tra bản cập nhật từ máy chủ S Editor")
        self.update_button.clicked.connect(self._check_update_manually)
        layout.addWidget(self.update_button)
        return update_bar

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("app_footer")
        footer.setMinimumHeight(54)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(6)

        for icon_name, text, url in (
            (
                "zalo.svg",
                "Nhóm Zalo",
                "https://zalo.me/g/2h4r4fbobrg66e9haa3q",
            ),
        ):
            icon = QLabel()
            icon.setPixmap(
                QPixmap(str(ICONS_DIR / icon_name)).scaled(
                    20,
                    20,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            label = QLabel(
                f'<a href="{url}" style="color: #93c5fd; '
                f'text-decoration: underline;">{text}</a>'
            )
            label.setOpenExternalLinks(True)
            label.setStyleSheet(
                "color: #93c5fd; font-size: 12px; font-weight: 600;"
            )
            layout.addWidget(icon)
            layout.addWidget(label)
            layout.addSpacing(18)

        layout.addStretch()
        self.footer_creator = QLabel("© Created by: botocIT")
        self.footer_creator.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        layout.addWidget(self.footer_creator)
        return footer

    def _check_update_automatically(self) -> None:
        self._clear_available_update()
        self._set_update_status("Đang kiểm tra cập nhật…", "#94a3b8")
        self._auto_updater = UpdateCheckerThread(self)
        self._auto_updater.update_available.connect(self._on_update_available)
        self._auto_updater.no_update.connect(self._on_no_update)
        self._auto_updater.check_failed.connect(self._on_update_check_failed)
        self._auto_updater.start()

    def _check_update_manually(self) -> None:
        self.update_button.setEnabled(False)
        self._clear_available_update()
        self._set_update_status("Đang kiểm tra cập nhật…", "#94a3b8")
        self._manual_updater = UpdateCheckerThread(self)
        self._manual_updater.update_available.connect(self._on_update_available)
        self._manual_updater.no_update.connect(
            self._on_no_update
        )
        self._manual_updater.no_update.connect(
            lambda message: QMessageBox.information(self, "Kiểm tra cập nhật", message)
        )
        self._manual_updater.check_failed.connect(
            self._on_update_check_failed
        )
        self._manual_updater.check_failed.connect(
            lambda message: QMessageBox.warning(self, "Kiểm tra cập nhật", message)
        )
        self._manual_updater.finished.connect(lambda: self.update_button.setEnabled(True))
        self._manual_updater.start()

    def _set_update_status(self, text: str, color: str) -> None:
        self.update_status_label.setText(text)
        self.update_status_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 600;"
        )

    def _on_no_update(self, _message: str) -> None:
        self._clear_available_update()
        self._set_update_status(f"✓ Đã cập nhật (v{APP_VERSION})", "#4ade80")

    def _on_update_available(self, update_info: dict) -> None:
        self.available_update_info = update_info
        self.install_update_button.setVisible(True)
        self._set_update_status(f"↑ Có bản mới v{update_info['version']}", "#fbbf24")
        self._show_update_dialog(update_info)

    def _on_update_check_failed(self, _message: str) -> None:
        self._clear_available_update()
        self._set_update_status("Không thể kiểm tra cập nhật", "#f87171")

    def _clear_available_update(self) -> None:
        self.available_update_info = None
        self.install_update_button.setVisible(False)

    def _open_available_update(self) -> None:
        if self.available_update_info:
            self._show_update_dialog(self.available_update_info)

    def _show_update_dialog(self, update_info: dict) -> None:
        UpdateDialog(update_info, self).exec()

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.core.standalone_state import StandaloneStateStore
from app.ui.watermark_tab import WatermarkTab


ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


class MainWindow(QMainWindow):
    """Giai đoạn 1: ứng dụng chỉ cung cấp công cụ gỡ watermark."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Editor v1.0")
        self.resize(1240, 820)
        self.setMinimumSize(900, 640)

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

        self.watermark_tab = WatermarkTab()
        self.watermark_tab.configure_standalone(
            self.standalone_state, config.WATERMARK_DOWNLOADS_DIR
        )
        root_layout.addWidget(self.watermark_tab, stretch=1)
        root_layout.addWidget(self._build_footer())

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
                "Hỗ trợ tại Zalo",
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
        creator = QLabel("© Created by: trtoan")
        creator.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: 600;")
        layout.addWidget(creator)
        return footer

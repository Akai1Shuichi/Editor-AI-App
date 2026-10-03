"""The update notice, download progress, and restart choice in one dialog."""

from html import escape

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout


class UpdateDialog(QDialog):
    download_requested = pyqtSignal()
    restart_requested = pyqtSignal()

    def __init__(self, version: str, notes: str, url: str | None, parent=None):
        super().__init__(parent)
        self._state = "available"
        self.setWindowTitle("Có bản cập nhật mới")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 16, 28, 16)
        layout.setSpacing(12)
        self.details_label = QLabel(
            f"<p>Đã có phiên bản {escape(version)}.</p>{notes}"
            + ("<p>Ứng dụng sẽ tải bản mới và hỏi khi có thể khởi động lại để cập nhật.</p>"
               if url else "<p>Máy chủ chưa cung cấp gói cập nhật phù hợp với hệ điều hành này.</p>")
        )
        self.details_label.setTextFormat(Qt.TextFormat.RichText)
        self.details_label.setWordWrap(True)
        layout.addWidget(self.details_label)

        self.status_label = QLabel()
        self.status_label.hide()
        layout.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.later_button = QPushButton("Để sau" if url else "Đóng")
        self.later_button.clicked.connect(self.reject)
        buttons.addWidget(self.later_button)
        self.download_button = QPushButton("Tải bản cập nhật")
        self.download_button.setVisible(bool(url))
        self.download_button.clicked.connect(self._on_primary_clicked)
        buttons.addWidget(self.download_button)
        layout.addLayout(buttons)

    def _on_primary_clicked(self) -> None:
        if self._state == "available":
            self.begin_download()
            self.download_requested.emit()
        elif self._state == "ready":
            self.accept()
            self.restart_requested.emit()

    def begin_download(self) -> None:
        if self._state != "available":
            return
        self._state = "downloading"
        self.status_label.setText("Đang tải bản cập nhật…")
        self.status_label.show()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.later_button.hide()
        self.download_button.hide()

    def set_progress(self, percent: int) -> None:
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)
        self.status_label.setText(f"Đang tải bản cập nhật: {percent}%")

    def show_ready(self, version: str) -> None:
        self._state = "ready"
        self.status_label.setText(f"Đã tải phiên bản {version}. Cập nhật và khởi động lại ngay?")
        self.progress_bar.hide()
        self.later_button.show()
        self.download_button.setText("Cập nhật và khởi động lại")
        self.download_button.show()

    def show_error(self, message: str) -> None:
        self._state = "error"
        self.status_label.setText(f"Không thể tải cập nhật: {message}")
        self.progress_bar.hide()
        self.later_button.setText("Đóng")
        self.later_button.show()

    def reject(self) -> None:
        if self._state != "downloading":
            super().reject()

    def closeEvent(self, event) -> None:
        if self._state == "downloading":
            event.ignore()
            return
        super().closeEvent(event)

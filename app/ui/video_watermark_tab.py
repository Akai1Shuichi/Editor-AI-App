from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.core.platform_utils import open_path
from app.core.video_watermark_remover import VideoWatermarkRemover


class VideoWatermarkWorker(QThread):
    progress_updated = pyqtSignal(int, str)
    processing_finished = pyqtSignal(bool, str, str)

    def __init__(self, source: Path, output: Path, gain: float, scale: float, offset_x: int, offset_y: int, parent=None):
        super().__init__(parent)
        self.source = source
        self.output = output
        self._cancelled = False
        self.gain, self.scale, self.offset_x, self.offset_y = gain, scale, offset_x, offset_y

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            def report(current: int, total: Optional[int]) -> None:
                percent = int(current * 100 / total) if total else 0
                self.progress_updated.emit(min(99, percent), f"Đang xử lý frame {current}/{total or '?'}…")

            result = VideoWatermarkRemover().process_file(
                self.source,
                self.output,
                gain=self.gain, scale=self.scale, offset_x=self.offset_x, offset_y=self.offset_y,
                progress_callback=report,
                is_cancelled=lambda: self._cancelled,
            )
            self.processing_finished.emit(
                bool(result.get("success")),
                str(result.get("output_path", self.output)),
                str(result.get("error", "Đã hủy xử lý." if result.get("cancelled") else "")),
            )
        except Exception as exc:
            self.processing_finished.emit(False, str(self.output), str(exc))


class VideoWatermarkTab(QWidget):
    """A local video counterpart to the existing image watermark workspace."""

    video_filter = "Video (*.mp4 *.mov *.mkv *.webm)"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_path: Optional[Path] = None
        self.output_path: Optional[Path] = None
        self.worker: Optional[VideoWatermarkWorker] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("Gỡ watermark Video")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)
        description = QLabel(
            "Xử lý cục bộ từng frame bằng cùng thuật toán unblending của ảnh. "
            "Video không được tải lên máy chủ."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(description)

        card = QFrame()
        card.setObjectName("watermark_controls")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        self.source_label = QLabel("Chưa chọn video")
        self.source_label.setWordWrap(True)
        self.output_label = QLabel("Kết quả sẽ lưu cạnh video gốc")
        self.output_label.setWordWrap(True)
        for label in (self.source_label, self.output_label):
            label.setStyleSheet("color: #cbd5e1; font-size: 12px;")
            card_layout.addWidget(label)

        pick_row = QHBoxLayout()
        self.choose_button = QPushButton("Chọn video…")
        self.choose_button.setObjectName("btn_primary")
        self.choose_button.clicked.connect(self.choose_video)
        self.destination_button = QPushButton("Đổi nơi lưu…")
        self.destination_button.setObjectName("btn_subtle")
        self.destination_button.setEnabled(False)
        self.destination_button.clicked.connect(self.choose_destination)
        pick_row.addWidget(self.choose_button)
        pick_row.addWidget(self.destination_button)
        pick_row.addStretch()
        card_layout.addLayout(pick_row)

        self.gain_slider, self.scale_slider, self.x_slider, self.y_slider = self._add_alignment_controls(card_layout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        card_layout.addWidget(self.progress)
        self.status = QLabel("Sẵn sàng.")
        self.status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        card_layout.addWidget(self.status)

        action_row = QHBoxLayout()
        self.start_button = QPushButton("Bắt đầu xử lý video")
        self.start_button.setObjectName("btn_primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_processing)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setObjectName("btn_danger")
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.open_button = QPushButton("Mở video kết quả")
        self.open_button.setObjectName("btn_subtle")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self.open_output)
        action_row.addWidget(self.start_button)
        action_row.addWidget(self.cancel_button)
        action_row.addWidget(self.open_button)
        card_layout.addLayout(action_row)
        layout.addWidget(card)
        layout.addStretch()

    def _add_alignment_controls(self, layout):
        controls = (("Strength (Gain)", 10, 90, 60, 100), ("Size Scale", 50, 150, 101, 100), ("Position X", -80, 40, -24, 1), ("Position Y", -160, 40, -24, 1))
        sliders = []
        for title, low, high, value, divisor in controls:
            row = QHBoxLayout(); label = QLabel(title); value_label = QLabel()
            slider = QSlider(Qt.Orientation.Horizontal); slider.setRange(low, high); slider.setValue(value)
            def refresh(_=0, s=slider, l=value_label, d=divisor): l.setText(f"{s.value()/d:.2f}×" if d == 100 else f"{s.value():+d}px")
            slider.valueChanged.connect(refresh); refresh(); row.addWidget(label); row.addWidget(slider, 1); row.addWidget(value_label); layout.addLayout(row); sliders.append(slider)
        return sliders

    def choose_video(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Chọn video", str(Path.home()), self.video_filter)
        if not filename:
            return
        self.source_path = Path(filename)
        self.output_path = self.source_path.with_name(f"{self.source_path.stem}_cleaned.mp4")
        # Keep the web-compatible defaults for every aspect ratio.  The core
        # converts these offsets from the Gemini/Veo video anchor; there is no
        # separate 9:16 correction.
        self.gain_slider.setValue(60)
        self.scale_slider.setValue(101)
        self.x_slider.setValue(-24)
        self.y_slider.setValue(-24)
        self.source_label.setText(f"Video nguồn: {self.source_path}")
        self.output_label.setText(f"Kết quả: {self.output_path}")
        self.destination_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.open_button.setEnabled(False)
        self.progress.setValue(0)
        self.status.setText("Sẵn sàng xử lý.")

    def choose_destination(self) -> None:
        if not self.output_path:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Lưu video đã xử lý", str(self.output_path), "MP4 Video (*.mp4)"
        )
        if filename:
            self.output_path = Path(filename)
            self.output_label.setText(f"Kết quả: {self.output_path}")

    def _set_running(self, running: bool) -> None:
        self.choose_button.setEnabled(not running)
        self.destination_button.setEnabled(not running and self.output_path is not None)
        self.start_button.setVisible(not running)
        self.start_button.setEnabled(not running and self.source_path is not None)
        self.cancel_button.setVisible(running)
        self.cancel_button.setEnabled(running)

    def start_processing(self) -> None:
        if not self.source_path or not self.output_path:
            return
        if self.output_path.exists():
            QMessageBox.warning(self, "File đã tồn tại", "Hãy chọn tên file kết quả khác để tránh ghi đè.")
            return
        self.progress.setValue(0)
        self.status.setText("Đang khởi tạo FFmpeg…")
        self._set_running(True)
        self.worker = VideoWatermarkWorker(self.source_path, self.output_path, self.gain_slider.value()/100, self.scale_slider.value()/100, self.x_slider.value(), self.y_slider.value(), self)
        self.worker.progress_updated.connect(self.on_progress)
        self.worker.processing_finished.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, percent: int, message: str) -> None:
        self.progress.setValue(percent)
        self.status.setText(message)

    def on_finished(self, success: bool, output: str, error: str) -> None:
        self._set_running(False)
        if success:
            self.progress.setValue(100)
            self.output_path = Path(output)
            self.status.setText("Hoàn tất gỡ watermark video.")
            self.open_button.setEnabled(True)
        else:
            self.status.setText(f"Không thể xử lý video: {error}")
            QMessageBox.warning(self, "Gỡ watermark Video", error)

    def cancel_processing(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status.setText("Đang dừng…")

    def open_output(self) -> None:
        if self.output_path and self.output_path.is_file():
            try:
                open_path(self.output_path)
            except OSError as exc:
                QMessageBox.warning(self, "Không thể mở video", str(exc))

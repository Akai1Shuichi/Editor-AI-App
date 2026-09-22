from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QVBoxLayout, QWidget,
)

from app.core.platform_utils import open_path
from app.core.standalone_state import build_output_folder_name, resolve_new_output_folder
from app import config
from app.core.video_watermark_remover import VideoWatermarkRemover


class VideoWatermarkWorker(QThread):
    """Sequential batch worker; the video engine remains independent of images."""
    file_processed = pyqtSignal(int, int, str, bool, str)
    finished_all = pyqtSignal(int, int)

    def __init__(self, files: List[Path], output_dir: Path, parent=None):
        super().__init__(parent)
        self.files, self.output_dir = files, output_dir
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total, success_count = len(self.files), 0
        try:
            remover = VideoWatermarkRemover()
            for current, source in enumerate(self.files, 1):
                if self._cancelled:
                    break
                output = self.output_dir / f"{source.stem}_cleaned.mp4"
                try:
                    result = remover.process_file(
                        source, output,
                        is_cancelled=lambda: self._cancelled,
                    )
                    success = bool(result.get("success"))
                    detail = str(result.get("output_path") if success else result.get("error", "Lỗi xử lý video"))
                    success_count += int(success)
                    self.file_processed.emit(current, total, source.name, success, detail)
                except Exception as exc:
                    self.file_processed.emit(current, total, source.name, False, str(exc))
        finally:
            self.finished_all.emit(total, success_count)


class VideoWatermarkTab(QWidget):
    """Batch video removal UI, deliberately aligned with the image workflow."""
    video_filter = "Video (*.mp4 *.mov *.mkv *.webm)"
    video_extensions = {".mp4", ".mov", ".mkv", ".webm"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("watermark_tab")
        self.selected_files: List[Path] = []
        self.output_dir: Optional[Path] = config.VIDEO_WATERMARK_DOWNLOADS_DIR
        self.current_run_dir: Optional[Path] = None
        self.worker: Optional[VideoWatermarkWorker] = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        title = QLabel("Gỡ watermark Video")
        title.setObjectName("tool_title")
        layout.addWidget(title)
        notice = QLabel("Lưu ý: Gỡ watermark video hiện chỉ hỗ trợ cho video 720p.")
        notice.setWordWrap(True)
        notice.setStyleSheet("color: #facc15; font-size: 12px;")
        layout.addWidget(notice)

        card = QFrame()
        card.setObjectName("watermark_controls")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 14, 14, 14)
        form.setSpacing(10)
        file_row = QHBoxLayout()
        self.choose_button = QPushButton("Chọn file video…")
        self.choose_button.setObjectName("btn_primary")
        self.choose_button.clicked.connect(self.choose_files)
        self.folder_button = QPushButton("Chọn thư mục…")
        self.folder_button.setObjectName("btn_subtle")
        self.folder_button.clicked.connect(self.choose_folder)
        for button in (self.choose_button, self.folder_button):
            file_row.addWidget(button)
        file_row.addStretch()
        form.addLayout(file_row)

        list_header = QHBoxLayout()
        list_title = QLabel("Danh sách video")
        list_title.setProperty("class", "section_label")
        self.file_count = QLabel("0 video")
        self.file_count.setObjectName("meta_label")
        self.remove_button = QPushButton("Xóa hàng đã chọn")
        self.remove_button.setObjectName("btn_subtle")
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button = QPushButton("Xóa hết")
        self.clear_button.setObjectName("btn_subtle")
        self.clear_button.clicked.connect(self.clear_files)
        list_header.addWidget(list_title)
        list_header.addWidget(self.file_count)
        list_header.addStretch()
        list_header.addWidget(self.remove_button)
        list_header.addWidget(self.clear_button)
        form.addLayout(list_header)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Video", "Trạng thái", "Kết quả / lỗi"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setMinimumHeight(220)
        self.table.itemSelectionChanged.connect(self._update_controls)
        form.addWidget(self.table)

        name_row = QHBoxLayout()
        name_label = QLabel("Tên thư mục kết quả:")
        name_label.setProperty("class", "section_label")
        name_row.addWidget(name_label)
        self.output_name = QLineEdit(build_output_folder_name("clean_video"))
        self.output_name.setPlaceholderText("clean_video_YYYYMMDD_HHMMSS")
        name_row.addWidget(self.output_name, 1)
        form.addLayout(name_row)

        destination = QHBoxLayout()
        destination.setSpacing(8)
        location_label = QLabel("Lưu tại:")
        location_label.setProperty("class", "section_label")
        self.destination_path_label = QLabel(str(self.output_dir))
        self.destination_path_label.setObjectName("output_path")
        self.destination_path_label.setToolTip(str(self.output_dir))
        self.destination_path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.destination_button = QPushButton("Chọn thư mục...")
        self.destination_button.setObjectName("btn_subtle")
        self.destination_button.clicked.connect(self.choose_destination)
        self.open_button = QPushButton("Mở thư mục video")
        self.open_button.setObjectName("btn_subtle")
        self.open_button.clicked.connect(self.open_output_directory)
        destination.addWidget(location_label)
        destination.addWidget(self.destination_path_label, 1)
        destination.addWidget(self.destination_button)
        destination.addWidget(self.open_button)
        form.addLayout(destination)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        form.addWidget(self.progress)
        self.status = QLabel("Chọn video để bắt đầu.")
        self.status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        form.addWidget(self.status)
        actions = QHBoxLayout()
        self.start_button = QPushButton("Bắt đầu xử lý danh sách")
        self.start_button.setObjectName("btn_primary")
        self.start_button.clicked.connect(self.start_processing)
        self.cancel_button = QPushButton("Hủy")
        self.cancel_button.setObjectName("btn_danger")
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setVisible(False)
        for button in (self.start_button, self.cancel_button):
            actions.addWidget(button)
        actions.addStretch()
        form.addLayout(actions)
        layout.addWidget(card)
        layout.addStretch()
        self._update_controls()

    def choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Chọn video cần gỡ watermark", str(Path.home()), self.video_filter)
        self.add_files([Path(file) for file in files])

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa video", str(Path.home()))
        if not folder:
            return
        files = [path for path in sorted(Path(folder).iterdir()) if path.is_file()
                 and path.suffix.lower() in self.video_extensions and not path.stem.endswith("_cleaned")]
        if files:
            self.add_files(files)
        else:
            QMessageBox.information(self, "Không có video", "Không tìm thấy video phù hợp trong thư mục này.")

    def add_files(self, paths: List[Path]) -> None:
        for path in paths:
            if path in self.selected_files or not path.is_file() or path.suffix.lower() not in self.video_extensions:
                continue
            self.selected_files.append(path)
            row = self.table.rowCount()
            self.table.insertRow(row)
            item = QTableWidgetItem(path.name)
            item.setToolTip(str(path))
            self.table.setItem(row, 0, item)
            self.table.setItem(row, 1, QTableWidgetItem("Chờ"))
            self.table.setItem(row, 2, QTableWidgetItem("-"))
        self.status.setText(f"Đã nạp {len(self.selected_files)} video.")
        self._update_file_count()
        self._update_controls()

    def choose_destination(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục gốc lưu video kết quả", str(self.output_dir))
        if folder:
            self.output_dir = Path(folder)
            self.destination_path_label.setText(str(self.output_dir))
            self.destination_path_label.setToolTip(str(self.output_dir))
            self._update_controls()

    def remove_selected(self) -> None:
        for row in sorted({index.row() for index in self.table.selectionModel().selectedRows()}, reverse=True):
            self.selected_files.pop(row)
            self.table.removeRow(row)
        self.status.setText(f"Còn {len(self.selected_files)} video.")
        self._update_file_count()
        self._update_controls()

    def clear_files(self) -> None:
        self.selected_files.clear()
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self.status.setText("Danh sách trống.")
        self._update_file_count()
        self._update_controls()

    def _update_file_count(self) -> None:
        self.file_count.setText(f"{len(self.selected_files)} video")

    def _output_directory(self) -> Path:
        return self.current_run_dir or self.output_dir or config.VIDEO_WATERMARK_DOWNLOADS_DIR

    def _set_running(self, running: bool) -> None:
        for widget in (self.choose_button, self.folder_button, self.remove_button, self.clear_button,
                       self.destination_button, self.output_name, self.table):
            widget.setEnabled(not running)
        self.start_button.setVisible(not running)
        self.start_button.setEnabled(not running and bool(self.selected_files))
        self.cancel_button.setVisible(running)
        self.cancel_button.setEnabled(running)
        self.open_button.setEnabled(not running and self._output_directory().is_dir())

    def _update_controls(self) -> None:
        if not self.worker or not self.worker.isRunning():
            self.start_button.setEnabled(bool(self.selected_files))
            self.remove_button.setEnabled(bool(self.table.selectionModel().selectedRows()))
            self.clear_button.setEnabled(bool(self.selected_files))
            self.open_button.setEnabled(self._output_directory().is_dir())

    def start_processing(self) -> None:
        if not self.selected_files:
            QMessageBox.warning(self, "Chưa có video", "Vui lòng chọn ít nhất một video.")
            return
        output_root = self.output_dir or config.VIDEO_WATERMARK_DOWNLOADS_DIR
        try:
            self.current_run_dir = resolve_new_output_folder(output_root, self.output_name.text())
            self.current_run_dir.mkdir(parents=True)
        except (ValueError, OSError) as exc:
            QMessageBox.warning(self, "Không thể tạo thư mục kết quả", str(exc))
            return
        self.progress.setValue(0)
        self.status.setText("Đang chuẩn bị xử lý video…")
        self._set_running(True)
        self.worker = VideoWatermarkWorker(self.selected_files, self.current_run_dir, self)
        self.worker.file_processed.connect(self.on_file_processed)
        self.worker.finished_all.connect(self.on_finished_all)
        self.worker.start()

    def on_file_processed(self, current: int, total: int, name: str, success: bool, detail: str) -> None:
        self.progress.setValue(int(current * 100 / total))
        state = QTableWidgetItem("✓ Xong" if success else "✗ Lỗi")
        state.setForeground(QColor("#34d399" if success else "#f87171"))
        self.table.setItem(current - 1, 1, state)
        item = QTableWidgetItem(detail)
        item.setToolTip(detail)
        self.table.setItem(current - 1, 2, item)
        self.status.setText(f"Đang xử lý ({current}/{total}): {name}")

    def on_finished_all(self, total: int, success_count: int) -> None:
        self._set_running(False)
        self.status.setText(f"Hoàn tất: {success_count}/{total} video.")
        self.output_name.setText(build_output_folder_name("clean_video"))

    def cancel_processing(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status.setText("Đang dừng sau video hiện tại…")

    def open_output_directory(self) -> None:
        try:
            open_path(self._output_directory())
        except OSError as exc:
            QMessageBox.warning(self, "Không thể mở thư mục", str(exc))

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QFrame, QMessageBox,
    QSplitter
)

from app.core.watermark_remover import GeminiWatermarkRemover
from app import config

class WatermarkWorker(QThread):
    """Worker xử lý gỡ watermark ngầm cho nhiều ảnh."""
    file_processed = pyqtSignal(int, int, str, bool, str)
    finished_all = pyqtSignal(int, int)

    def __init__(self, file_paths: List[Path], output_dir: Optional[Path], gain: float = 0.6, preset_mode: str = "auto"):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.gain = gain
        self.preset_mode = preset_mode
        self._is_cancelled = False
        self.remover = GeminiWatermarkRemover()

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        total = len(self.file_paths)
        success_count = 0

        for i, file_path in enumerate(self.file_paths):
            if self._is_cancelled:
                break

            try:
                out_name = f"{file_path.stem}_cleaned.png"
                if self.output_dir:
                    out_path = self.output_dir / out_name
                else:
                    # Tạo folder 'clean' trong folder chứa ảnh vừa nhập để tránh lộn xộn
                    clean_dir = file_path.parent / "clean"
                    clean_dir.mkdir(parents=True, exist_ok=True)
                    out_path = clean_dir / out_name

                res = self.remover.process_file(
                    file_path=file_path,
                    output_path=out_path,
                    gain=self.gain,
                    preset_mode=self.preset_mode
                )

                if res.get("success"):
                    success_count += 1
                    self.file_processed.emit(i + 1, total, file_path.name, True, str(out_path))
                else:
                    self.file_processed.emit(i + 1, total, file_path.name, False, res.get("error", "Lỗi xử lý"))
            except Exception as e:
                self.file_processed.emit(i + 1, total, file_path.name, False, str(e))

        self.finished_all.emit(total, success_count)


class DropArea(QFrame):
    """Khu vực kéo thả ảnh nhỏ gọn, hiện đại."""
    files_dropped = pyqtSignal(list)
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("drop_area")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        lbl_icon = QLabel("📥")
        lbl_icon.setStyleSheet("font-size: 16px;")
        lbl_text = QLabel("Kéo thả ảnh vào đây, hoặc click để chọn file (PNG, JPG, WEBP)")
        lbl_text.setStyleSheet("color: #9ca3af; font-weight: 500; font-size: 12px;")

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        paths = []
        valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file() and p.suffix.lower() in valid_exts:
                paths.append(p)
            elif p.is_dir():
                for sub in p.iterdir():
                    if sub.is_file() and sub.suffix.lower() in valid_exts:
                        paths.append(sub)
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class WatermarkTab(QWidget):
    """Tab chức năng Gỡ Watermark - Thiết kế tinh giản, tối ưu không gian."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("watermark_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.selected_files: List[Path] = []
        self.output_dir: Optional[Path] = None
        self.worker: Optional[WatermarkWorker] = None
        self.project = None
        self.init_ui()

    def set_project(self, project):
        """Cập nhật thông tin dự án hiện tại."""
        previous_slug = getattr(self.project, "slug", None)
        next_slug = getattr(project, "slug", None)
        if previous_slug != next_slug and hasattr(self, "table"):
            self.clear_file_list()
        self.project = project
        if project:
            self.lbl_project_badge.setText("Kết quả: images/clean")
            self.lbl_project_badge.setStyleSheet("color: #70798a; font-size: 11px;")
            self.output_dir = project.clean_images_dir
            self.chk_custom_out.setChecked(True)
            self.chk_custom_out.setVisible(False)
            self.btn_custom_out.setVisible(False)
        else:
            self.lbl_project_badge.setText("📁 Chưa chọn dự án")
            self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
            self.output_dir = None
            self.chk_custom_out.setChecked(False)
            self.chk_custom_out.setText("Lưu thư mục riêng")
            self.chk_custom_out.setVisible(True)
            self.btn_custom_out.setVisible(True)

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("content_container")

        # ================= CỘT TRÁI: ĐIỀU KHIỂN & DANH SÁCH =================
        left_box = QWidget()
        left_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        left_layout = QVBoxLayout(left_box)
        left_layout.setContentsMargins(0, 0, 8, 0)
        left_layout.setSpacing(10)

        # Drop Area
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.on_files_selected)
        self.drop_area.clicked.connect(self.choose_files)
        left_layout.addWidget(self.drop_area)

        # Toolbar chọn file
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(8)

        self.btn_select_files = QPushButton("Chọn File Ảnh")
        self.btn_select_files.clicked.connect(self.choose_files)

        self.btn_select_folder = QPushButton("Chọn Thư Mục")
        self.btn_select_folder.clicked.connect(self.choose_folder)

        self.btn_clear_list = QPushButton("Xóa Danh Sách")
        self.btn_clear_list.setObjectName("btn_subtle")
        self.btn_clear_list.clicked.connect(self.clear_file_list)

        btn_bar.addWidget(self.btn_select_files)
        btn_bar.addWidget(self.btn_select_folder)
        btn_bar.addStretch()
        btn_bar.addWidget(self.btn_clear_list)
        left_layout.addLayout(btn_bar)

        # Bảng danh sách file ảnh
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Tên File", "Trạng Thái", "Đường Dẫn Kết Quả"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        left_layout.addWidget(self.table)

        # Cấu hình lưu trữ (Gọn trong 1 dòng)
        settings_panel = QFrame()
        settings_panel.setProperty("class", "panel")
        settings_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        s_layout = QHBoxLayout(settings_panel)
        s_layout.setContentsMargins(10, 8, 10, 8)
        s_layout.setSpacing(14)

        # Project Badge & Output option
        self.lbl_project_badge = QLabel("📁 Chưa chọn dự án")
        self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
        s_layout.addWidget(self.lbl_project_badge)

        self.chk_custom_out = QCheckBox("Lưu thư mục riêng")
        self.chk_custom_out.setToolTip("Mặc định ảnh sạch sẽ được lưu vào thư mục 'clean' của dự án hoặc thư mục ảnh gốc.")
        self.chk_custom_out.toggled.connect(self.toggle_custom_out)
        self.btn_custom_out = QPushButton("Chọn...")
        self.btn_custom_out.setEnabled(False)
        self.btn_custom_out.clicked.connect(self.choose_output_folder)

        s_layout.addWidget(self.chk_custom_out)
        s_layout.addWidget(self.btn_custom_out)
        s_layout.addStretch()

        left_layout.addWidget(settings_panel)

        # Thanh thực thi Action
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self.btn_start = QPushButton("Bắt đầu xử lý")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.clicked.connect(self.start_processing)

        self.btn_cancel = QPushButton("Dừng")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)

        self.btn_open_folder = QPushButton("Mở thư mục ảnh")
        self.btn_open_folder.clicked.connect(self.open_output_dir)

        action_layout.addWidget(self.btn_start, stretch=2)
        action_layout.addWidget(self.btn_cancel)
        action_layout.addWidget(self.btn_open_folder)
        left_layout.addLayout(action_layout)

        # Progress bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.status_lbl = QLabel("Sẵn sàng. Chưa có ảnh nào được chọn.")
        self.status_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")

        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.status_lbl)

        splitter.addWidget(left_box)

        # ================= CỘT PHẢI: XEM TRƯỚC (BEFORE / AFTER) =================
        right_box = QWidget()
        right_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(10)

        # Preview Ảnh Gốc
        lbl_p1 = QLabel("Ảnh gốc:")
        lbl_p1.setProperty("class", "section_label")
        self.lbl_preview_orig = QLabel("Chưa chọn ảnh")
        self.lbl_preview_orig.setObjectName("preview_frame")
        self.lbl_preview_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_orig.setStyleSheet("color: #6b7280; min-height: 200px;")

        # Preview Ảnh Đã Gỡ
        lbl_p2 = QLabel("Kết quả sau khi gỡ:")
        lbl_p2.setProperty("class", "section_label")
        self.lbl_preview_clean = QLabel("Chưa có kết quả")
        self.lbl_preview_clean.setObjectName("preview_frame")
        self.lbl_preview_clean.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_clean.setStyleSheet("color: #6b7280; min-height: 200px;")

        right_layout.addWidget(lbl_p1)
        right_layout.addWidget(self.lbl_preview_orig, stretch=1)
        right_layout.addWidget(lbl_p2)
        right_layout.addWidget(self.lbl_preview_clean, stretch=1)

        splitter.addWidget(right_box)
        splitter.setSizes([600, 360])

        main_layout.addWidget(splitter)

    def choose_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn ảnh cần gỡ watermark",
            str(Path.home()),
            "Ảnh (*.png *.jpg *.jpeg *.webp)"
        )
        if files:
            self.on_files_selected([Path(f) for f in files])

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa ảnh", str(Path.home()))
        if folder:
            p = Path(folder)
            valid_exts = {".png", ".jpg", ".jpeg", ".webp"}
            found = [f for f in p.iterdir() if f.is_file() and f.suffix.lower() in valid_exts and not f.stem.endswith("_cleaned")]
            if found:
                self.on_files_selected(found)
            else:
                QMessageBox.information(self, "Thông báo", "Không tìm thấy file ảnh phù hợp trong thư mục!")

    def toggle_custom_out(self, checked: bool):
        self.btn_custom_out.setEnabled(checked)
        if checked and not self.output_dir:
            self.choose_output_folder()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu file kết quả", str(Path.home()))
        if folder:
            self.output_dir = Path(folder)
            self.btn_custom_out.setText(f"📁 {self.output_dir.name}")

    def on_files_selected(self, paths: List[Path]):
        for p in paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
                row = self.table.rowCount()
                self.table.insertRow(row)
                item_file = QTableWidgetItem(p.name)
                item_file.setToolTip(str(p))
                self.table.setItem(row, 0, item_file)
                self.table.setItem(row, 1, QTableWidgetItem("Chờ"))
                self.table.setItem(row, 2, QTableWidgetItem("-"))

        self.status_lbl.setText(f"Đã nạp {len(self.selected_files)} ảnh.")
        if self.selected_files:
            self.display_image_preview(self.selected_files[0], self.lbl_preview_orig)

    def clear_file_list(self):
        self.selected_files.clear()
        self.table.setRowCount(0)
        self.lbl_preview_orig.setText("Chưa chọn ảnh")
        self.lbl_preview_clean.setText("Chưa có kết quả")
        self.status_lbl.setText("Danh sách trống.")
        self.progress_bar.setValue(0)

    def display_image_preview(self, path: Path, label: QLabel):
        if not path.exists():
            return
        pixmap = QPixmap(str(path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            label.setPixmap(scaled)

    def on_table_selection_changed(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.selected_files):
            orig_path = self.selected_files[row]
            self.display_image_preview(orig_path, self.lbl_preview_orig)

            clean_item = self.table.item(row, 2)
            if clean_item and clean_item.text() != "-":
                clean_path = Path(clean_item.text())
                if clean_path.exists():
                    self.display_image_preview(clean_path, self.lbl_preview_clean)
                else:
                    self.lbl_preview_clean.setText("File không tồn tại")
            else:
                self.lbl_preview_clean.setText("Chưa xử lý")

    def start_processing(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Chưa chọn file", "Vui lòng thêm ít nhất 1 ảnh để xử lý!")
            return

        gain = 0.6
        preset_mode = "auto"
        if self.chk_custom_out.isChecked() and self.output_dir:
            out_dir = self.output_dir
        elif self.project:
            out_dir = self.project.clean_images_dir
        else:
            out_dir = None

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setMaximum(len(self.selected_files))
        self.progress_bar.setValue(0)
        self.status_lbl.setText("Đang xử lý...")

        self.worker = WatermarkWorker(self.selected_files, out_dir, gain, preset_mode)
        self.worker.file_processed.connect(self.on_file_processed)
        self.worker.finished_all.connect(self.on_finished_all)
        self.worker.start()

    def on_file_processed(self, current: int, total: int, filename: str, success: bool, msg: str):
        self.progress_bar.setValue(current)
        row = current - 1
        if success:
            item_status = QTableWidgetItem("Xong")
            item_status.setForeground(Qt.GlobalColor.green)
            self.table.setItem(row, 1, item_status)
            item_res = QTableWidgetItem(msg)
            item_res.setToolTip(msg)
            self.table.setItem(row, 2, item_res)
            clean_path = Path(msg)
            if clean_path.exists():
                self.display_image_preview(clean_path, self.lbl_preview_clean)
        else:
            item_status = QTableWidgetItem("Lỗi")
            item_status.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 1, item_status)
            self.table.setItem(row, 2, QTableWidgetItem(msg))

        self.status_lbl.setText(f"Đang xử lý ({current}/{total}): {filename}")

    def on_finished_all(self, total: int, success_count: int):
        self.btn_start.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if success_count and self.project:
            self.project.save_metadata()
        target_name = self.output_dir.name if self.output_dir else (self.project.clean_images_dir.name if self.project else "clean")
        self.status_lbl.setText(f"Hoàn thành: {success_count}/{total} file (lưu tại '{target_name}').")

    def cancel_processing(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_lbl.setText("Đang dừng...")
            self.btn_cancel.setEnabled(False)

    def open_output_dir(self):
        target = self.output_dir
        if not target and self.project and self.project.clean_images_dir.exists():
            target = self.project.clean_images_dir
        elif not target and self.selected_files:
            clean_dir = self.selected_files[0].parent / "clean"
            target = clean_dir if clean_dir.exists() else self.selected_files[0].parent
        if not target:
            target = config.DOWNLOADS_DIR

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target)])
            else:
                subprocess.run(["xdg-open", str(target)])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {e}")

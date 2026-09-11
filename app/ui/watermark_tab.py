import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor
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

    images_updated = pyqtSignal()

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
            clean_count = len(project.get_clean_images())
            raw_count = len(project.get_raw_images())
            if clean_count > 0:
                self.lbl_project_badge.setText(f"✓ {clean_count} ảnh sạch sẵn sàng")
                self.lbl_project_badge.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 600;")
            elif raw_count > 0:
                self.lbl_project_badge.setText(f"{raw_count} ảnh gốc chờ xử lý")
                self.lbl_project_badge.setStyleSheet("color: #facc15; font-size: 11px;")
            else:
                self.lbl_project_badge.setText("Kết quả: images/clean")
                self.lbl_project_badge.setStyleSheet("color: #70798a; font-size: 11px;")

            self.output_dir = project.clean_images_dir
            self.chk_custom_out.setChecked(True)
            self.chk_custom_out.setVisible(False)
            self.btn_custom_out.setVisible(False)

            # Tự động nạp danh sách ảnh đã có của dự án
            self._hydrate_project_images(project)
        else:
            self.lbl_project_badge.setText("📁 Chưa chọn dự án")
            self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
            self.output_dir = None
            self.chk_custom_out.setChecked(False)
            self.chk_custom_out.setText("Lưu thư mục riêng")
            self.chk_custom_out.setVisible(True)
            self.btn_custom_out.setVisible(True)

        self.images_updated.emit()

    def _hydrate_project_images(self, project):
        """Nạp ảnh sạch hoặc ảnh gốc đã có vào danh sách để người dùng thấy ngay."""
        clean_imgs = project.get_clean_images()
        if clean_imgs:
            self.selected_files = list(clean_imgs)
            self.table.setRowCount(0)
            for row, p in enumerate(clean_imgs):
                self.table.insertRow(row)
                item_file = QTableWidgetItem(p.name)
                item_file.setToolTip(str(p))
                self.table.setItem(row, 0, item_file)

                item_status = QTableWidgetItem("✓ Sẵn sàng")
                item_status.setForeground(QColor("#34d399"))
                self.table.setItem(row, 1, item_status)
                self.table.setItem(row, 2, QTableWidgetItem("Đã gỡ watermark"))

            self.status_lbl.setText(f"✓ Dự án có {len(clean_imgs)} ảnh sạch sẵn sàng cho video.")
            self.display_image_preview(clean_imgs[0], self.lbl_preview_orig)
            self.display_image_preview(clean_imgs[0], self.lbl_preview_clean)
        else:
            raw_imgs = project.get_raw_images()
            if raw_imgs:
                self.selected_files = list(raw_imgs)
                self.table.setRowCount(0)
                for row, p in enumerate(raw_imgs):
                    self.table.insertRow(row)
                    item_file = QTableWidgetItem(p.name)
                    item_file.setToolTip(str(p))
                    self.table.setItem(row, 0, item_file)
                    self.table.setItem(row, 1, QTableWidgetItem("Chờ"))
                    self.table.setItem(row, 2, QTableWidgetItem("-"))
                self.status_lbl.setText(f"Có {len(raw_imgs)} ảnh gốc trong thư mục images/, bấm Bắt đầu để xử lý.")
                self.display_image_preview(raw_imgs[0], self.lbl_preview_orig)

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
        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)

        self.btn_select_files = QPushButton("Chọn File Ảnh...")
        self.btn_select_files.clicked.connect(self.choose_files)

        self.btn_select_folder = QPushButton("Chọn Thư Mục")
        self.btn_select_folder.setObjectName("btn_subtle")
        self.btn_select_folder.clicked.connect(self.choose_folder)

        self.btn_clear = QPushButton("Xóa Hết")
        self.btn_clear.setObjectName("btn_subtle")
        self.btn_clear.clicked.connect(self.clear_file_list)

        btn_box.addWidget(self.btn_select_files)
        btn_box.addWidget(self.btn_select_folder)
        btn_box.addWidget(self.btn_clear)
        left_layout.addLayout(btn_box)

        # Cấu hình lưu file ra
        out_box = QHBoxLayout()
        out_box.setSpacing(8)

        self.lbl_project_badge = QLabel("📁 Chưa chọn dự án")
        self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")

        self.chk_custom_out = QCheckBox("Lưu thư mục riêng")
        self.chk_custom_out.setToolTip("Mặc định ảnh sạch sẽ được lưu vào thư mục 'clean' của dự án hoặc thư mục ảnh gốc.")
        self.chk_custom_out.toggled.connect(self.toggle_custom_out)

        self.btn_custom_out = QPushButton("Chọn thư mục...")
        self.btn_custom_out.setEnabled(False)
        self.btn_custom_out.setObjectName("btn_subtle")
        self.btn_custom_out.clicked.connect(self.choose_output_folder)

        out_box.addWidget(self.lbl_project_badge)
        out_box.addStretch()
        out_box.addWidget(self.chk_custom_out)
        out_box.addWidget(self.btn_custom_out)
        left_layout.addLayout(out_box)

        # Bảng danh sách file
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Tên File", "Trạng Thái", "Thời Gian"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.cellClicked.connect(self.on_table_row_clicked)
        left_layout.addWidget(self.table)

        # Thanh thực thi
        action_box = QHBoxLayout()
        action_box.setSpacing(8)

        self.btn_start = QPushButton("Bắt Đầu Xử Lý")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.clicked.connect(self.start_processing)

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_processing)

        self.btn_open_folder = QPushButton("Mở thư mục ảnh")
        self.btn_open_folder.setObjectName("btn_subtle")
        self.btn_open_folder.clicked.connect(self.open_output_dir)

        action_box.addWidget(self.btn_start, stretch=2)
        action_box.addWidget(self.btn_cancel)
        action_box.addWidget(self.btn_open_folder)
        left_layout.addLayout(action_box)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Sẵn sàng.")
        self.status_lbl.setStyleSheet("color: #6b7280; font-size: 11px;")
        left_layout.addWidget(self.status_lbl)

        splitter.addWidget(left_box)

        # ================= CỘT PHẢI: XEM TRƯỚC (PREVIEW) =================
        right_box = QWidget()
        right_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        right_layout = QVBoxLayout(right_box)
        right_layout.setContentsMargins(8, 0, 0, 0)
        right_layout.setSpacing(8)

        lbl_p1 = QLabel("Ảnh gốc (Trước khi xử lý):")
        lbl_p1.setProperty("class", "section_label")
        self.lbl_preview_orig = QLabel("Chưa chọn ảnh")
        self.lbl_preview_orig.setObjectName("preview_box")
        self.lbl_preview_orig.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_orig.setStyleSheet("color: #6b7280; min-height: 200px;")

        lbl_p2 = QLabel("Kết quả sạch (Đã gỡ watermark):")
        lbl_p2.setProperty("class", "section_label")
        self.lbl_preview_clean = QLabel("Chưa có kết quả")
        self.lbl_preview_clean.setObjectName("preview_box")
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
        self.images_updated.emit()

    def clear_file_list(self):
        self.selected_files.clear()
        self.table.setRowCount(0)
        self.lbl_preview_orig.setText("Chưa chọn ảnh")
        self.lbl_preview_clean.setText("Chưa có kết quả")
        self.status_lbl.setText("Danh sách trống.")
        self.progress_bar.setValue(0)
        self.images_updated.emit()

    def display_image_preview(self, path: Path, label: QLabel):
        if not path.exists():
            return
        pix = QPixmap(str(path))
        if not pix.isNull():
            label.setPixmap(pix.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

    def on_table_row_clicked(self, row: int, col: int):
        if 0 <= row < len(self.selected_files):
            orig_p = self.selected_files[row]
            self.display_image_preview(orig_p, self.lbl_preview_orig)

            # Nếu ảnh đã là ảnh sạch hoặc có file sạch tương ứng
            if "_cleaned" in orig_p.stem or (self.project and orig_p.parent == self.project.clean_images_dir):
                self.display_image_preview(orig_p, self.lbl_preview_clean)
            else:
                out_dir = self.output_dir or (self.project.clean_images_dir if self.project else orig_p.parent / "clean")
                clean_p = out_dir / f"{orig_p.stem}_cleaned.png"
                if clean_p.exists():
                    self.display_image_preview(clean_p, self.lbl_preview_clean)
                else:
                    self.lbl_preview_clean.setText("Chưa có kết quả")

    def start_processing(self):
        if not self.selected_files:
            QMessageBox.warning(self, "Chưa có file", "Vui lòng chọn hoặc kéo thả ít nhất 1 ảnh!")
            return

        out_dir = self.output_dir or (self.project.clean_images_dir if self.project else None)

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_lbl.setText("Đang chuẩn bị...")

        self.worker = WatermarkWorker(
            file_paths=self.selected_files,
            output_dir=out_dir
        )
        self.worker.file_processed.connect(self.on_file_processed)
        self.worker.finished_all.connect(self.on_finished_all)
        self.worker.start()

    def on_file_processed(self, current: int, total: int, filename: str, success: bool, msg: str):
        pct = int(current / total * 100)
        self.progress_bar.setValue(pct)

        row = current - 1
        if 0 <= row < self.table.rowCount():
            item_status = QTableWidgetItem("✓ Xong" if success else "✗ Lỗi")
            item_status.setForeground(QColor("#34d399" if success else "#f87171"))
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
        self.images_updated.emit()

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

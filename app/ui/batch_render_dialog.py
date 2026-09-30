from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.batch_render import (
    BatchRenderWorker,
    BatchStatus,
    validate_project_for_render,
)
from app.core.platform_utils import open_path
from app.core.project_manager import Project


class BatchRenderDialog(QDialog):
    """Hộp thoại điều khiển và theo dõi tiến trình Xuất Video Hàng Loạt cho nhiều dự án."""

    batch_finished = pyqtSignal(dict)  # Phát tín hiệu khi toàn bộ hàng đợi hoàn tất

    def __init__(self, projects: List[Project], parent=None):
        super().__init__(parent)
        self.setObjectName("batch_render_dialog")
        self.setWindowTitle("Xuất Video Hàng Loạt (Batch Render)")
        self.setModal(True)
        self.resize(920, 620)
        self.setMinimumSize(800, 500)

        self.projects = list(projects)
        self.worker: Optional[BatchRenderWorker] = None
        self.project_rows: Dict[str, int] = {}
        self.validations: Dict[str, Dict[str, Any]] = {}

        self._build_ui()
        self._inspect_projects()
        self._update_summary()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 18)
        root.setSpacing(14)

        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        title = QLabel("Xuất Video Hàng Loạt (Batch Render)")
        title.setObjectName("dialog_title")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #f9fafb;")
        subtitle = QLabel(
            "Xử lý lần lượt từng dự án theo hàng đợi an toàn để tối ưu hiệu năng CPU/GPU."
        )
        subtitle.setObjectName("page_subtitle")
        subtitle.setStyleSheet("font-size: 12px; color: #9ca3af;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addLayout(header_layout)

        # Thanh cấu hình tùy chọn xuất
        config_frame = QFrame()
        config_frame.setStyleSheet(
            "background-color: #171821; border: 1px solid #252836; border-radius: 8px; padding: 6px 12px;"
        )
        config_layout = QHBoxLayout(config_frame)
        config_layout.setContentsMargins(8, 6, 8, 6)
        config_layout.setSpacing(16)

        lbl_opt = QLabel("Tùy chọn xuất:")
        lbl_opt.setStyleSheet("font-weight: 600; color: #e5e7eb; font-size: 12px;")
        config_layout.addWidget(lbl_opt)

        config_layout.addWidget(QLabel("Tỷ lệ:"))
        self.combo_ratio = QComboBox()
        self.combo_ratio.addItem("Theo từng dự án", "")
        self.combo_ratio.addItem("16:9 — Ngang", "16:9")
        self.combo_ratio.addItem("9:16 — Dọc", "9:16")
        self.combo_ratio.addItem("1:1 — Vuông", "1:1")
        config_layout.addWidget(self.combo_ratio)

        config_layout.addWidget(QLabel("Tốc độ:"))
        self.combo_fps = QComboBox()
        self.combo_fps.addItem("Theo từng dự án", 0)
        self.combo_fps.addItem("30 FPS", 30)
        self.combo_fps.addItem("24 FPS", 24)
        self.combo_fps.addItem("60 FPS", 60)
        config_layout.addWidget(self.combo_fps)

        self.chk_skip_invalid = QCheckBox("Bỏ qua dự án thiếu tài nguyên")
        self.chk_skip_invalid.setChecked(True)
        config_layout.addWidget(self.chk_skip_invalid)

        config_layout.addStretch()
        root.addWidget(config_frame)

        # Bảng danh sách dự án trong hàng đợi
        self.table = QTableWidget()
        self.table.setObjectName("batch_table")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            [
                "DỰ ÁN",
                "TỶ LỆ / FPS",
                "TÀI NGUYÊN",
                "TIẾN ĐỘ",
                "TRẠNG THÁI",
                "THAO TÁC",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for col in (1, 2, 4):
            self.table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().resizeSection(3, 140)
        self.table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().resizeSection(5, 110)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        root.addWidget(self.table, stretch=1)

        # Khu vực tiến trình tổng thể & dự án hiện tại
        progress_box = QFrame()
        progress_box.setStyleSheet(
            "background-color: #171821; border: 1px solid #252836; border-radius: 8px; padding: 10px 14px;"
        )
        progress_layout = QVBoxLayout(progress_box)
        progress_layout.setContentsMargins(10, 8, 10, 8)
        progress_layout.setSpacing(6)

        # Tiến độ dự án hiện tại
        row_curr = QHBoxLayout()
        self.lbl_curr_task = QLabel("Dự án hiện tại: Sẵn sàng")
        self.lbl_curr_task.setStyleSheet("color: #e5e7eb; font-weight: 500; font-size: 12px;")
        self.lbl_curr_pct = QLabel("0%")
        self.lbl_curr_pct.setStyleSheet("color: #60a5fa; font-weight: 600; font-size: 12px;")
        row_curr.addWidget(self.lbl_curr_task)
        row_curr.addStretch()
        row_curr.addWidget(self.lbl_curr_pct)
        progress_layout.addLayout(row_curr)

        self.bar_current = QProgressBar()
        self.bar_current.setRange(0, 100)
        self.bar_current.setValue(0)
        self.bar_current.setTextVisible(False)
        self.bar_current.setFixedHeight(8)
        progress_layout.addWidget(self.bar_current)

        # Tiến độ toàn bộ hàng đợi
        row_queue = QHBoxLayout()
        self.lbl_queue_task = QLabel("Tổng tiến độ: 0/0 dự án")
        self.lbl_queue_task.setStyleSheet("color: #9ca3af; font-size: 11px;")
        self.lbl_queue_pct = QLabel("0%")
        self.lbl_queue_pct.setStyleSheet("color: #34d399; font-weight: 600; font-size: 11px;")
        row_queue.addWidget(self.lbl_queue_task)
        row_queue.addStretch()
        row_queue.addWidget(self.lbl_queue_pct)
        progress_layout.addLayout(row_queue)

        self.bar_queue = QProgressBar()
        self.bar_queue.setRange(0, 100)
        self.bar_queue.setValue(0)
        self.bar_queue.setTextVisible(False)
        self.bar_queue.setFixedHeight(8)
        progress_layout.addWidget(self.bar_queue)

        root.addWidget(progress_box)

        # Footer hành động
        footer = QHBoxLayout()
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("color: #9ca3af; font-size: 12px;")
        footer.addWidget(self.lbl_summary)
        footer.addStretch()

        self.btn_cancel = QPushButton("Dừng hàng loạt")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_batch)
        footer.addWidget(self.btn_cancel)

        self.btn_close = QPushButton("Đóng")
        self.btn_close.clicked.connect(self.accept)
        footer.addWidget(self.btn_close)

        self.btn_start = QPushButton(f"🚀 Bắt đầu xuất ({len(self.projects)} dự án)")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setDefault(True)
        self.btn_start.clicked.connect(self.start_batch)
        footer.addWidget(self.btn_start)

        root.addLayout(footer)

    def _inspect_projects(self):
        """Quét và kiểm tra tính sẵn sàng của tất cả các dự án trong danh sách."""
        self.table.setRowCount(len(self.projects))
        self.project_rows.clear()
        self.validations.clear()

        for row, project in enumerate(self.projects):
            self.project_rows[project.slug] = row
            val = validate_project_for_render(project)
            self.validations[project.slug] = val

            self.table.setRowHeight(row, 46)

            # Cột 0: Dự án
            item_name = QTableWidgetItem(f"{project.name}\n{project.slug}")
            item_name.setForeground(QColor("#F3F5F7"))
            self.table.setItem(row, 0, item_name)

            # Cột 1: Tỷ lệ / FPS
            item_ratio = QTableWidgetItem(f"{project.aspect_ratio} • {project.fps}fps")
            item_ratio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_ratio.setForeground(QColor("#9CA3AF"))
            self.table.setItem(row, 1, item_ratio)

            # Cột 2: Tài nguyên
            if val["is_ready"]:
                res_text = f"✓ Đủ tài nguyên ({val['images_count']} ảnh)"
                res_color = "#34D399"
            else:
                reasons = ", ".join(val["missing_reasons"])
                res_text = f"⚠ Thiếu ({len(val['missing_reasons'])})"
                res_color = "#F87171"
            item_res = QTableWidgetItem(res_text)
            item_res.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_res.setForeground(QColor(res_color))
            if not val["is_ready"]:
                item_res.setToolTip("\n".join(val["missing_reasons"]))
            self.table.setItem(row, 2, item_res)

            # Cột 3: Tiến độ (ProgressBar trong ô)
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(0)
            pbar.setTextVisible(True)
            pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pbar.setFixedHeight(18)
            self.table.setCellWidget(row, 3, pbar)

            # Cột 4: Trạng thái
            status_item = QTableWidgetItem("Chờ xuất")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor("#9CA3AF"))
            self.table.setItem(row, 4, status_item)

            # Cột 5: Thao tác (ban đầu trống)
            action_holder = QWidget()
            self.table.setCellWidget(row, 5, action_holder)

    def _update_summary(self):
        total = len(self.projects)
        ready_count = sum(1 for val in self.validations.values() if val["is_ready"])
        unready_count = total - ready_count

        if unready_count == 0:
            self.lbl_summary.setText(f"✓ Tất cả {total} dự án đã sẵn sàng để xuất.")
        else:
            self.lbl_summary.setText(
                f"Đã chọn: {total} dự án ({ready_count} sẵn sàng, {unready_count} thiếu tài nguyên)."
            )

        self.btn_start.setEnabled(ready_count > 0 or not self.chk_skip_invalid.isChecked())

    def start_batch(self):
        """Khởi động luồng render hàng loạt qua BatchRenderWorker."""
        custom_ratio = self.combo_ratio.currentData() or None
        custom_fps = int(self.combo_fps.currentData() or 0) or None
        skip_invalid = self.chk_skip_invalid.isChecked()

        self.btn_start.setEnabled(False)
        self.btn_start.setVisible(False)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)
        self.btn_close.setEnabled(False)
        self.combo_ratio.setEnabled(False)
        self.combo_fps.setEnabled(False)
        self.chk_skip_invalid.setEnabled(False)

        self.worker = BatchRenderWorker(
            projects=self.projects,
            custom_ratio=custom_ratio,
            custom_fps=custom_fps,
            skip_invalid=skip_invalid,
        )

        self.worker.project_started.connect(self._on_project_started)
        self.worker.project_progress.connect(self._on_project_progress)
        self.worker.project_finished.connect(self._on_project_finished)
        self.worker.queue_progress.connect(self._on_queue_progress)
        self.worker.batch_completed.connect(self._on_batch_completed)

        self.worker.start()

    def cancel_batch(self):
        """Yêu cầu dừng hàng loạt an toàn."""
        if self.worker and self.worker.isRunning():
            self.btn_cancel.setEnabled(False)
            self.lbl_curr_task.setText("Đang yêu cầu dừng hàng loạt...")
            self.worker.cancel()

    def _on_project_started(self, slug: str, index: int, total: int):
        row = self.project_rows.get(slug)
        if row is not None:
            status_item = self.table.item(row, 4)
            if status_item:
                status_item.setText("Đang xuất…")
                status_item.setForeground(QColor("#60A5FA"))

        project_name = next((p.name for p in self.projects if p.slug == slug), slug)
        self.lbl_curr_task.setText(f"Dự án [{index}/{total}]: {project_name}")
        self.bar_current.setValue(0)
        self.lbl_curr_pct.setText("0%")

    def _on_project_progress(self, slug: str, pct: int, msg: str):
        row = self.project_rows.get(slug)
        if row is not None:
            pbar = self.table.cellWidget(row, 3)
            if isinstance(pbar, QProgressBar):
                pbar.setValue(pct)

        self.bar_current.setValue(pct)
        self.lbl_curr_pct.setText(f"{pct}%")
        self.lbl_curr_task.setToolTip(msg)

    def _on_project_finished(self, slug: str, success: bool, info: dict):
        row = self.project_rows.get(slug)
        if row is None:
            return

        status = info.get("status", BatchStatus.COMPLETED.value if success else BatchStatus.FAILED.value)
        status_item = self.table.item(row, 4)

        if status == BatchStatus.COMPLETED.value:
            if status_item:
                status_item.setText("Hoàn tất")
                status_item.setForeground(QColor("#34D399"))
            pbar = self.table.cellWidget(row, 3)
            if isinstance(pbar, QProgressBar):
                pbar.setValue(100)

            # Gắn nút "Mở video"
            out_path_str = info.get("output_path")
            if out_path_str and Path(out_path_str).exists():
                out_path = Path(out_path_str)
                btn_open = QPushButton("Mở video")
                btn_open.setToolTip(f"Mở video: {out_path.name}")
                btn_open.clicked.connect(lambda _, p=out_path: open_path(p))
                self.table.setCellWidget(row, 5, btn_open)

        elif status == BatchStatus.SKIPPED.value:
            if status_item:
                status_item.setText("Đã bỏ qua")
                status_item.setForeground(QColor("#FBBF24"))
                status_item.setToolTip(info.get("error_message", ""))
        elif status == BatchStatus.CANCELLED.value:
            if status_item:
                status_item.setText("Đã hủy")
                status_item.setForeground(QColor("#9CA3AF"))
        else:
            if status_item:
                status_item.setText("Thất bại")
                status_item.setForeground(QColor("#F87171"))
                status_item.setToolTip(info.get("error_message", "Lỗi xuất video"))

    def _on_queue_progress(self, current_index: int, total_count: int, overall_pct: int):
        self.bar_queue.setValue(overall_pct)
        self.lbl_queue_pct.setText(f"{overall_pct}%")
        self.lbl_queue_task.setText(f"Tổng tiến độ: {current_index}/{total_count} dự án ({overall_pct}%)")

    def _on_batch_completed(self, summary: dict):
        self.btn_cancel.setVisible(False)
        self.btn_close.setEnabled(True)
        self.btn_start.setVisible(True)
        self.btn_start.setEnabled(True)
        self.combo_ratio.setEnabled(True)
        self.combo_fps.setEnabled(True)
        self.chk_skip_invalid.setEnabled(True)

        comp = summary.get("completed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        cancelled = summary.get("cancelled", 0)

        self.lbl_curr_task.setText("Đã hoàn tất đợt xuất video hàng loạt.")
        self.lbl_summary.setText(
            f"Kết quả: {comp} thành công, {failed} lỗi, {skipped} bỏ qua, {cancelled} hủy."
        )

        self.batch_finished.emit(summary)

        # Thông báo hoàn tất
        QMessageBox.information(
            self,
            "Hoàn tất xuất hàng loạt",
            (
                f"Đã hoàn thành xuất video hàng loạt!\n\n"
                f"• Thành công: {comp} dự án\n"
                f"• Thất bại: {failed} dự án\n"
                f"• Bỏ qua: {skipped} dự án\n"
                f"• Đã hủy: {cancelled} dự án"
            ),
        )

    def closeEvent(self, event):
        """Xử lý an toàn khi người dùng cố gắng đóng cửa sổ trong khi đang xuất."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Đang xuất video",
                "Quá trình xuất video hàng loạt đang diễn ra.\nBạn có chắc muốn hủy và đóng lại?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.cancel()
                self.worker.wait(3000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

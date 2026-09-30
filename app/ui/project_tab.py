from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QEvent, QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QIcon
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from app.core.project_manager import Project, ProjectManager, slugify
from app.core.platform_utils import open_path
from app.core.batch_render import validate_project_for_render
from app.ui.batch_render_dialog import BatchRenderDialog

YOUTUBE_TUTORIAL_URL = "https://youtu.be/SwU7mc58AXA?si=MHx7uoIvZFKHL430"
YOUTUBE_ICON = Path(__file__).resolve().parent.parent / "assets" / "icons" / "youtube.svg"


class NewProjectDialog(QDialog):
    """Thu thập cấu hình tối thiểu và hiển thị trước thư mục dự án."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("new_project_dialog")
        self.setWindowTitle("Tạo dự án mới")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._build_ui()
        self._update_preview()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)

        title = QLabel("Tạo dự án mới")
        title.setObjectName("dialog_title")
        subtitle = QLabel("Thiết lập không gian làm việc cho video mới.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        form = QFormLayout()
        form.setContentsMargins(0, 4, 0, 0)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Ví dụ: Review công nghệ tháng 9")
        self.txt_name.textChanged.connect(self._update_preview)
        form.addRow("Tên dự án", self.txt_name)

        self.combo_ratio = QComboBox()
        self.combo_ratio.addItem("16:9 — Ngang", "16:9")
        self.combo_ratio.addItem("9:16 — Dọc", "9:16")
        self.combo_ratio.addItem("1:1 — Vuông", "1:1")
        form.addRow("Tỷ lệ khung hình", self.combo_ratio)

        self.combo_fps = QComboBox()
        for fps in (30, 24, 25, 60):
            self.combo_fps.addItem(f"{fps} FPS", fps)
        form.addRow("Tốc độ khung hình", self.combo_fps)
        layout.addLayout(form)

        preview_box = QFrame()
        preview_box.setObjectName("path_preview")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(4)
        preview_label = QLabel("Thư mục sẽ được tạo")
        preview_label.setObjectName("meta_label")
        self.lbl_path = QLabel()
        self.lbl_path.setObjectName("path_value")
        self.lbl_error = QLabel()
        self.lbl_error.setObjectName("field_error")
        self.lbl_error.setWordWrap(True)
        preview_layout.addWidget(preview_label)
        preview_layout.addWidget(self.lbl_path)
        preview_layout.addWidget(self.lbl_error)
        layout.addWidget(preview_box)

        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Hủy")
        cancel.clicked.connect(self.reject)
        self.btn_create = QPushButton("Tạo và mở dự án")
        self.btn_create.setObjectName("btn_primary")
        self.btn_create.setDefault(True)
        self.btn_create.clicked.connect(self._submit)
        buttons.addWidget(cancel)
        buttons.addWidget(self.btn_create)
        layout.addLayout(buttons)

        self.txt_name.setFocus()

    def _update_preview(self):
        name = self.txt_name.text().strip()
        slug = slugify(name) if name else "ten-du-an"
        self.lbl_path.setText(str(ProjectManager.get_projects_root() / slug))

        exists = bool(name) and (ProjectManager.get_projects_root() / slug).exists()
        self.lbl_error.setText(
            f"Thư mục '{slug}' đã tồn tại. Vui lòng chọn tên khác."
            if exists
            else ""
        )
        self.btn_create.setEnabled(bool(name) and not exists)

    def _submit(self):
        if not self.txt_name.text().strip():
            self.lbl_error.setText("Tên dự án không được để trống.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "name": self.txt_name.text().strip(),
            "aspect_ratio": self.combo_ratio.currentData() or "16:9",
            "fps": int(self.combo_fps.currentData() or 30),
        }


class ProjectTab(QWidget):
    """Danh sách dự án là điểm vào duy nhất của workspace."""

    project_activated = pyqtSignal(str)
    project_deleted = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("project_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.projects: List[Project] = []
        self.visible_projects: List[Project] = []
        self.selected_slug: Optional[str] = None
        self.selected_batch_slugs: set[str] = set()
        self._build_ui()
        self.refresh_projects()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        header_text.setSpacing(3)
        title = QLabel("Dự án")
        title.setObjectName("page_heading")
        subtitle = QLabel("Quản lý và tiếp tục các nội dung đang sản xuất.")
        subtitle.setObjectName("page_subtitle")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)
        header.addLayout(header_text)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setObjectName("project_search")
        self.search.setPlaceholderText("Tìm dự án…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(250)
        self.search.textChanged.connect(self._apply_filters)
        header.addWidget(self.search)

        self.btn_batch = QPushButton("🚀  Xuất hàng loạt")
        self.btn_batch.setObjectName("btn_primary")
        self.btn_batch.setToolTip("Xuất video hàng loạt cho các dự án đã chọn")
        self.btn_batch.setEnabled(False)
        self.btn_batch.clicked.connect(self.open_batch_render_dialog)
        header.addWidget(self.btn_batch)

        create = QPushButton("+  Dự án mới")
        create.setObjectName("btn_primary")
        create.clicked.connect(self.show_new_project_dialog)
        header.addWidget(create)
        layout.addLayout(header)

        tutorial_button = QPushButton("Hướng dẫn tạo video hoạt hình 2D Người Que  ↗")
        tutorial_button.setObjectName("btn_tutorial")
        tutorial_button.setIcon(QIcon(str(YOUTUBE_ICON)))
        tutorial_button.setIconSize(QSize(22, 18))
        tutorial_button.setToolTip("Xem video hướng dẫn trên YouTube")
        tutorial_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(YOUTUBE_TUTORIAL_URL))
        )
        layout.addWidget(tutorial_button, alignment=Qt.AlignmentFlag.AlignLeft)

        controls = QHBoxLayout()
        self.lbl_count = QLabel("0 dự án")
        self.lbl_count.setObjectName("section_heading")
        controls.addWidget(self.lbl_count)

        self.lbl_selected_batch = QLabel("Đã chọn: 0")
        self.lbl_selected_batch.setStyleSheet(
            "color: #60a5fa; font-weight: 600; font-size: 12px; margin-left: 10px; margin-right: 6px;"
        )
        controls.addWidget(self.lbl_selected_batch)

        btn_select_all = QPushButton("Chọn tất cả")
        btn_select_all.setObjectName("btn_subtle")
        btn_select_all.clicked.connect(self.select_all_projects)
        controls.addWidget(btn_select_all)

        btn_select_ready = QPushButton("Chọn dự án sẵn sàng")
        btn_select_ready.setObjectName("btn_subtle")
        btn_select_ready.clicked.connect(self.select_ready_projects)
        controls.addWidget(btn_select_ready)

        btn_deselect = QPushButton("Bỏ chọn")
        btn_deselect.setObjectName("btn_subtle")
        btn_deselect.clicked.connect(self.deselect_all_projects)
        controls.addWidget(btn_deselect)

        controls.addStretch()
        controls.addWidget(QLabel("Sắp xếp"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Cập nhật gần nhất", "updated")
        self.sort_combo.addItem("Tên A–Z", "name")
        self.sort_combo.addItem("Ngày tạo", "created")
        self.sort_combo.currentIndexChanged.connect(self._apply_filters)
        controls.addWidget(self.sort_combo)
        refresh = QPushButton("Làm mới")
        refresh.setObjectName("btn_subtle")
        refresh.clicked.connect(self.refresh_projects)
        controls.addWidget(refresh)
        layout.addLayout(controls)

        self.content_stack = QStackedWidget()

        self.table = QTableWidget()
        self.table.setObjectName("project_table")
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                "TÊN DỰ ÁN",
                "TỶ LỆ",
                "ẢNH",
                "GIỌNG NÓI",
                "VIDEO",
                "CẬP NHẬT",
                "THAO TÁC",
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().resizeSection(0, 42)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        for column in (2, 3, 4, 5):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            7, QHeaderView.ResizeMode.Fixed
        )
        self.table.horizontalHeader().resizeSection(7, 200)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(lambda _: self.open_selected_project())
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.installEventFilter(self)
        self.content_stack.addWidget(self.table)

        empty = QWidget()
        empty_layout = QVBoxLayout(empty)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.setSpacing(8)
        empty_title = QLabel("Chưa có dự án")
        empty_title.setObjectName("empty_title")
        empty_text = QLabel("Tạo dự án đầu tiên để bắt đầu quy trình sản xuất.")
        empty_text.setObjectName("page_subtitle")
        empty_create = QPushButton("+  Tạo dự án")
        empty_create.setObjectName("btn_primary")
        empty_create.clicked.connect(self.show_new_project_dialog)
        empty_layout.addStretch()
        empty_layout.addWidget(empty_title, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addSpacing(8)
        empty_layout.addWidget(empty_create, alignment=Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch()
        self.content_stack.addWidget(empty)
        layout.addWidget(self.content_stack, stretch=1)

    def eventFilter(self, watched, event):
        if (
            watched is self.table
            and event.type() == QEvent.Type.KeyPress
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            self.open_selected_project()
            return True
        return super().eventFilter(watched, event)

    def refresh_projects(self):
        """Đọc lại dữ liệu và giữ lựa chọn nếu dự án vẫn tồn tại."""
        self.projects = ProjectManager.list_projects()
        self._apply_filters()

    def _apply_filters(self):
        query = self.search.text().strip().casefold()
        projects = [
            project
            for project in self.projects
            if not query
            or query in project.name.casefold()
            or query in project.slug.casefold()
        ]

        sort_key = self.sort_combo.currentData()
        if sort_key == "name":
            projects.sort(key=lambda project: project.name.casefold())
        elif sort_key == "created":
            projects.sort(key=lambda project: project.created_at, reverse=True)
        else:
            projects.sort(key=lambda project: project.updated_at, reverse=True)

        self.visible_projects = projects
        self.lbl_count.setText(f"{len(projects)} dự án")
        self.content_stack.setCurrentIndex(0 if projects else 1)
        self._populate_table()

    def _populate_table(self):
        selected_slug = self.selected_slug
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.visible_projects))

        selected_row = -1
        for row, project in enumerate(self.visible_projects):
            stats = project.stats()
            self.table.setRowHeight(row, 58)

            # Cột 0: Checkbox chọn dự án xuất hàng loạt
            chk_container = QWidget()
            chk_layout = QHBoxLayout(chk_container)
            chk_layout.setContentsMargins(10, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chk = QCheckBox()
            chk.setChecked(project.slug in self.selected_batch_slugs)
            chk.toggled.connect(
                lambda checked, s=project.slug: self._on_batch_checkbox_toggled(s, checked)
            )
            chk_layout.addWidget(chk)
            self.table.setCellWidget(row, 0, chk_container)

            # Cột 1: Tên dự án
            name = QTableWidgetItem(f"{project.name}\nprojects/{project.slug}")
            name.setData(Qt.ItemDataRole.UserRole, project.slug)
            name.setForeground(QColor("#F3F5F7"))
            self.table.setItem(row, 1, name)

            # Cột 2: Tỷ lệ
            ratio = QTableWidgetItem(project.aspect_ratio)
            ratio.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, ratio)

            # Cột 3: Ảnh
            clean_count = stats["clean_images_count"]
            raw_count = stats["raw_images_count"]
            image_text = (
                f"{clean_count}/{raw_count}" if raw_count else f"{clean_count}"
            )
            images = QTableWidgetItem(image_text)
            images.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, images)

            # Cột 4: Giọng nói
            if stats["has_voice"] and stats["has_srt"]:
                voice_text = "Sẵn sàng"
                voice_color = "#35C58A"
            elif stats["has_voice"]:
                voice_text = "Thiếu SRT"
                voice_color = "#F2B84B"
            else:
                voice_text = "Chưa có"
                voice_color = "#70798A"
            voice = QTableWidgetItem(voice_text)
            voice.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            voice.setForeground(QColor(voice_color))
            self.table.setItem(row, 4, voice)

            # Cột 5: Video
            count = stats["videos_count"]
            videos = QTableWidgetItem(f"{count} bản" if count else "Chưa xuất")
            videos.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            videos.setForeground(QColor("#35C58A" if count else "#70798A"))
            self.table.setItem(row, 5, videos)

            # Cột 6: Cập nhật
            updated = QTableWidgetItem(f"{self._format_date(project.updated_at)}    ›")
            updated.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.table.setItem(row, 6, updated)

            # Cột 7: Thao tác
            actions = QWidget()
            actions_layout = QHBoxLayout(actions)
            actions_layout.setContentsMargins(16, 5, 8, 5)
            actions_layout.setSpacing(8)

            folder_button = QPushButton("Mở thư mục")
            folder_button.setFixedWidth(102)
            folder_button.setToolTip(f"Mở thư mục dự án {project.name}")
            folder_button.clicked.connect(
                lambda _, slug=project.slug: self.open_project_folder(slug)
            )
            actions_layout.addWidget(folder_button)

            delete_button = QPushButton("Xóa")
            delete_button.setFixedWidth(50)
            delete_button.setObjectName("btn_danger")
            delete_button.setToolTip(f"Xóa dự án {project.name}")
            delete_button.clicked.connect(
                lambda _, slug=project.slug: self.delete_project(slug)
            )
            actions_layout.addWidget(delete_button)
            self.table.setCellWidget(row, 7, actions)

            if project.slug == selected_slug:
                selected_row = row

        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.selected_slug = None

        self._update_batch_buttons()

    @staticmethod
    def _format_date(value: str) -> str:
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%d/%m/%Y %H:%M")
        except (TypeError, ValueError):
            return "Không rõ"

    def _project_for_row(self, row: int) -> Optional[Project]:
        if 0 <= row < len(self.visible_projects):
            return self.visible_projects[row]
        return None

    def _selected_project(self) -> Optional[Project]:
        if not self.selected_slug:
            return None
        return next(
            (p for p in self.visible_projects if p.slug == self.selected_slug),
            None,
        )

    def _on_selection_changed(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.selected_slug = None
            return

        project = self._project_for_row(rows[0].row())
        if not project:
            return
        self.selected_slug = project.slug

    def _on_cell_clicked(self, row: int, column: int):
        if column == 6:
            project = self._project_for_row(row)
            if project:
                self.selected_slug = project.slug
                self.open_selected_project()

    def _on_batch_checkbox_toggled(self, slug: str, checked: bool):
        if checked:
            self.selected_batch_slugs.add(slug)
        else:
            self.selected_batch_slugs.discard(slug)
        self._update_batch_buttons()

    def select_all_projects(self):
        self.selected_batch_slugs = {p.slug for p in self.visible_projects}
        self._update_table_checkboxes()
        self._update_batch_buttons()

    def select_ready_projects(self):
        ready_slugs = set()
        for p in self.visible_projects:
            val = validate_project_for_render(p)
            if val["is_ready"]:
                ready_slugs.add(p.slug)
        self.selected_batch_slugs = ready_slugs
        self._update_table_checkboxes()
        self._update_batch_buttons()

    def deselect_all_projects(self):
        self.selected_batch_slugs.clear()
        self._update_table_checkboxes()
        self._update_batch_buttons()

    def _update_table_checkboxes(self):
        self.table.blockSignals(True)
        for row, project in enumerate(self.visible_projects):
            cell_widget = self.table.cellWidget(row, 0)
            if cell_widget:
                chk = cell_widget.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(project.slug in self.selected_batch_slugs)
                    chk.blockSignals(False)
        self.table.blockSignals(False)

    def _update_batch_buttons(self):
        count = len(self.selected_batch_slugs)
        self.lbl_selected_batch.setText(f"Đã chọn: {count}")
        if count > 0:
            self.btn_batch.setText(f"🚀  Xuất hàng loạt ({count})")
            self.btn_batch.setEnabled(True)
        else:
            self.btn_batch.setText("🚀  Xuất hàng loạt")
            self.btn_batch.setEnabled(False)

    def open_batch_render_dialog(self):
        if not self.selected_batch_slugs:
            QMessageBox.information(
                self,
                "Chưa chọn dự án",
                "Vui lòng tích chọn ít nhất một dự án trong danh sách để xuất video hàng loạt.",
            )
            return

        selected_projects = [
            p for p in self.projects if p.slug in self.selected_batch_slugs
        ]
        if not selected_projects:
            return

        dialog = BatchRenderDialog(selected_projects, parent=self)
        dialog.batch_finished.connect(lambda _: self.refresh_projects())
        dialog.exec()
        self.refresh_projects()

    def open_selected_project(self):
        project = self._selected_project()
        if not project:
            return
        if not project.path.exists():
            QMessageBox.warning(
                self,
                "Không thể mở dự án",
                "Dự án không còn tồn tại. Danh sách sẽ được làm mới.",
            )
            self.refresh_projects()
            return
        self.project_activated.emit(project.slug)

    def show_new_project_dialog(self):
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            project = ProjectManager.create_project(**dialog.get_data())
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể tạo dự án", str(exc))
            return
        self.refresh_projects()
        self.selected_slug = project.slug
        self.project_activated.emit(project.slug)

    def open_project_folder(self, slug: str):
        project = next((p for p in self.visible_projects if p.slug == slug), None)
        if project:
            self.open_folder(project.path)

    def delete_project(self, slug: str):
        project = next((p for p in self.visible_projects if p.slug == slug), None)
        if not project:
            return
        reply = QMessageBox.question(
            self,
            "Xóa dự án",
            (
                f"Xóa toàn bộ dự án “{project.name}”?\n\n"
                "Ảnh, giọng nói, phụ đề và video trong dự án sẽ bị xóa."
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        if not ProjectManager.delete_project(project.slug):
            QMessageBox.warning(
                self, "Không thể xóa dự án", "Hệ thống không thể xóa thư mục dự án."
            )
            return
        deleted_slug = project.slug
        self.selected_slug = None
        self.selected_batch_slugs.discard(deleted_slug)
        self.refresh_projects()
        self.project_deleted.emit(deleted_slug)

    @staticmethod
    def open_folder(folder_path: Path):
        try:
            open_path(folder_path)
        except OSError as exc:
            QMessageBox.warning(None, "Không thể mở thư mục", str(exc))

import os
import subprocess
import sys
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.project_manager import Project, ProjectManager
from app.ui.project_tab import ProjectTab
from app.ui.tts_tab import TTSTab
from app.ui.video_tab import VideoTab
from app.ui.watermark_tab import WatermarkTab


class ProjectWorkspace(QWidget):
    """Điều hướng từ danh sách dự án vào pipeline của một dự án cụ thể."""

    project_changed = pyqtSignal(str)

    LIST_PAGE = 0
    WORKSPACE_PAGE = 1

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("project_workspace")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.current_project: Optional[Project] = None
        self._build_ui()
        self.show_project_list(force=True)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.stack = QStackedWidget()
        self.stack.setObjectName("workspace_stack")
        root.addWidget(self.stack)

        self.project_list = ProjectTab()
        self.project_list.project_activated.connect(self.open_project)
        self.project_list.project_deleted.connect(self._on_project_deleted)
        self.stack.addWidget(self.project_list)

        self.workspace_page = QWidget()
        self.workspace_page.setObjectName("workspace_page")
        workspace_layout = QVBoxLayout(self.workspace_page)
        workspace_layout.setContentsMargins(22, 16, 22, 18)
        workspace_layout.setSpacing(12)

        header = QFrame()
        header.setObjectName("workspace_header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 12)
        header_layout.setSpacing(12)

        self.btn_back = QPushButton("←  Danh sách dự án")
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(self.show_project_list)
        header_layout.addWidget(self.btn_back)

        separator = QLabel("/")
        separator.setObjectName("breadcrumb_separator")
        header_layout.addWidget(separator)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.lbl_project_name = QLabel("Chưa mở dự án")
        self.lbl_project_name.setObjectName("workspace_title")
        self.lbl_updated = QLabel("")
        self.lbl_updated.setObjectName("meta_label")
        title_box.addWidget(self.lbl_project_name)
        title_box.addWidget(self.lbl_updated)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.badge_ratio = QLabel("—")
        self.badge_ratio.setObjectName("project_meta")
        self.badge_fps = QLabel("—")
        self.badge_fps.setObjectName("project_meta")
        header_layout.addWidget(self.badge_ratio)
        header_layout.addWidget(self.badge_fps)

        self.btn_menu = QPushButton("•••")
        self.btn_menu.setObjectName("btn_icon")
        self.btn_menu.setToolTip("Tùy chọn dự án")
        self.btn_menu.setFixedWidth(42)
        menu = QMenu(self.btn_menu)
        open_folder_action = QAction("Mở thư mục", self)
        open_folder_action.triggered.connect(self.open_current_project_folder)
        rename_action = QAction("Đổi tên", self)
        rename_action.triggered.connect(self.rename_current_project)
        delete_action = QAction("Xóa dự án…", self)
        delete_action.triggered.connect(self.delete_current_project)
        menu.addAction(open_folder_action)
        menu.addAction(rename_action)
        menu.addSeparator()
        menu.addAction(delete_action)
        self.btn_menu.setMenu(menu)
        header_layout.addWidget(self.btn_menu)
        workspace_layout.addWidget(header)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setObjectName("project_inner_tabs")
        self.inner_tabs.setDocumentMode(True)

        self.watermark_tab = WatermarkTab()
        self.tts_tab = TTSTab()
        self.video_tab = VideoTab()

        self.inner_tabs.addTab(self.watermark_tab, "1   Ảnh")
        self.inner_tabs.addTab(self.tts_tab, "2   Giọng nói")
        self.inner_tabs.addTab(self.video_tab, "3   Xuất video")
        workspace_layout.addWidget(self.inner_tabs, stretch=1)
        self.stack.addWidget(self.workspace_page)

        self.tts_tab.send_to_video.connect(self._on_tts_send_to_video)

    def show_project_list(self, checked=False, force=False):
        """Quay về danh sách; không cho đổi ngữ cảnh khi worker còn chạy."""
        if not force and self._has_running_task():
            QMessageBox.warning(
                self,
                "Tác vụ đang chạy",
                "Hãy dừng tác vụ hiện tại trước khi quay lại danh sách dự án.",
            )
            return
        self.project_list.refresh_projects()
        self.stack.setCurrentIndex(self.LIST_PAGE)

    def open_project(self, slug: str):
        project = ProjectManager.get_project(slug)
        if not project:
            QMessageBox.warning(
                self,
                "Không thể mở dự án",
                "Dự án không còn tồn tại. Danh sách sẽ được làm mới.",
            )
            self.show_project_list(force=True)
            return

        ProjectManager.set_active_project(project.slug)
        self.set_project(project)
        self.inner_tabs.setCurrentIndex(0)
        self.stack.setCurrentIndex(self.WORKSPACE_PAGE)

    def set_project(self, project: Project):
        self.current_project = project
        self.lbl_project_name.setText(project.name)
        self.lbl_updated.setText(
            f"Cập nhật {self._format_updated_at(project.updated_at)}"
        )
        self.badge_ratio.setText(project.aspect_ratio)
        self.badge_fps.setText(f"{project.fps} FPS")

        self.watermark_tab.set_project(project)
        self.tts_tab.set_project(project)
        self.video_tab.set_project(project)
        self.project_changed.emit(project.slug)

    def navigate_to_pipeline_step(self, step_index: int):
        if not self.current_project:
            return
        self.inner_tabs.setCurrentIndex(max(0, min(2, step_index - 1)))
        self.stack.setCurrentIndex(self.WORKSPACE_PAGE)

    def _on_tts_send_to_video(self, audio_path: str, srt_path: str):
        self.video_tab.set_audio_and_srt(audio_path, srt_path)
        self.inner_tabs.setCurrentIndex(2)

    def _on_project_deleted(self, slug: str):
        if self.current_project and self.current_project.slug == slug:
            self._clear_current_project()

    def rename_current_project(self):
        if not self.current_project:
            return
        name, accepted = QInputDialog.getText(
            self,
            "Đổi tên dự án",
            "Tên dự án",
            text=self.current_project.name,
        )
        if not accepted:
            return
        try:
            project = ProjectManager.rename_project(
                self.current_project.slug, name
            )
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể đổi tên", str(exc))
            return
        self.set_project(project)

    def delete_current_project(self):
        if not self.current_project:
            return
        if self._has_running_task():
            QMessageBox.warning(
                self,
                "Tác vụ đang chạy",
                "Hãy dừng tác vụ hiện tại trước khi xóa dự án.",
            )
            return

        project = self.current_project
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
        self._clear_current_project()
        self.show_project_list(force=True)

    def _clear_current_project(self):
        self.current_project = None
        self.watermark_tab.set_project(None)
        self.tts_tab.set_project(None)
        self.video_tab.set_project(None)
        self.project_changed.emit("")

    def _has_running_task(self) -> bool:
        return any(
            worker is not None and worker.isRunning()
            for worker in (
                getattr(self.watermark_tab, "worker", None),
                getattr(self.tts_tab, "worker", None),
                getattr(self.video_tab, "worker", None),
            )
        )

    def open_current_project_folder(self):
        if not self.current_project or not self.current_project.path.exists():
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self.current_project.path))
            elif sys.platform == "darwin":
                subprocess.run(
                    ["open", str(self.current_project.path)], check=False
                )
            else:
                subprocess.run(
                    ["xdg-open", str(self.current_project.path)], check=False
                )
        except OSError as exc:
            QMessageBox.warning(self, "Không thể mở thư mục", str(exc))

    @staticmethod
    def _format_updated_at(value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y lúc %H:%M")
        except (TypeError, ValueError):
            return "không rõ"

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QPainter
from PyQt6.QtWidgets import (
    QCheckBox,
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
from app.core.platform_utils import open_path
from app.ui.project_tab import ProjectTab
from app.ui.scene_tab import SceneTab
from app.ui.tts_tab import TTSTab
from app.ui.video_tab import VideoTab
from app.ui.watermark_tab import WatermarkTab
from app.ui.widgets import ToggleSwitch


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
        header.setMaximumHeight(64)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(12)

        self.btn_back = QPushButton("←  Dự án")
        self.btn_back.setObjectName("btn_back")
        self.btn_back.clicked.connect(self.show_project_list)
        header_layout.addWidget(self.btn_back)

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

        auto_save_label = QLabel("Tự động lưu")
        auto_save_label.setObjectName("meta_label")
        header_layout.addWidget(auto_save_label)

        self.action_auto_save = ToggleSwitch(self)
        self.action_auto_save.setToolTip("Tự động lưu thay đổi trong dự án")
        self.action_auto_save.toggled.connect(self._on_auto_save_toggled)
        header_layout.addWidget(self.action_auto_save)

        self.btn_save = QPushButton("Lưu")
        self.btn_save.setObjectName("btn_subtle")
        self.btn_save.setToolTip("Lưu toàn bộ kịch bản, cấu hình và trạng thái của dự án")
        self.btn_save.clicked.connect(self.save_project_manually)
        header_layout.addWidget(self.btn_save)

        self.btn_menu = QPushButton("•••")
        self.btn_menu.setObjectName("btn_icon")
        self.btn_menu.setToolTip("Tùy chọn dự án")
        self.btn_menu.setFixedWidth(42)
        menu = QMenu(self.btn_menu)
        rename_action = QAction("Đổi tên", self)
        rename_action.triggered.connect(self.rename_current_project)
        menu.addAction(rename_action)
        self.btn_menu.setMenu(menu)
        header_layout.addWidget(self.btn_menu)
        workspace_layout.addWidget(header)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setObjectName("project_inner_tabs")
        self.inner_tabs.setDocumentMode(True)

        self.watermark_tab = WatermarkTab()
        self.tts_tab = TTSTab()
        self.scene_tab = SceneTab()
        self.video_tab = VideoTab()

        self.inner_tabs.addTab(self.watermark_tab, "1  Ảnh")
        self.inner_tabs.addTab(self.tts_tab, "2  Giọng nói")
        self.inner_tabs.addTab(self.scene_tab, "3  Kịch bản cảnh")
        self.inner_tabs.addTab(self.video_tab, "4  Dựng video")
        workspace_layout.addWidget(self.inner_tabs, stretch=1)
        self.stack.addWidget(self.workspace_page)

        self.watermark_tab.images_updated.connect(self.refresh_pipeline_badges)
        self.tts_tab.voice_generated.connect(self._on_voice_generated)
        self.scene_tab.scene_path_changed.connect(self.video_tab.set_json_file)
        self.scene_tab.scenes_updated.connect(self.refresh_pipeline_badges)
        self.video_tab.video_rendered.connect(self._on_video_rendered)
        self.inner_tabs.currentChanged.connect(self._on_inner_tab_changed)

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
        self.lbl_updated.setText(self._project_meta_text())

        self.watermark_tab.set_project(project)
        self.tts_tab.set_project(project)
        self.video_tab.set_project(project)
        self.scene_tab.set_project(project)
        self.tts_tab.set_auto_save(self.action_auto_save.isChecked())
        self.scene_tab.set_auto_save(self.action_auto_save.isChecked())
        self.video_tab.set_auto_save(self.action_auto_save.isChecked())
        self.project_changed.emit(project.slug)
        self.refresh_pipeline_badges()

    def _on_auto_save_toggled(self, checked: bool):
        """Khi người dùng bật/tắt checkbox Tự động lưu."""
        self.tts_tab.set_auto_save(checked)
        self.scene_tab.set_auto_save(checked)
        self.video_tab.set_auto_save(checked)
        if checked:
            self.save_project_manually(silent=True)

    def navigate_to_pipeline_step(self, step_index: int):
        if not self.current_project:
            return
        self.inner_tabs.setCurrentIndex(max(0, min(3, step_index - 1)))
        self.stack.setCurrentIndex(self.WORKSPACE_PAGE)

    def _on_voice_generated(self, audio_path: str, srt_path: str):
        """Khi tạo voice xong ở tab 2, tự động ghi ngay file voice.mp3 và voice.srt sang tab 4."""
        self.video_tab.set_audio_and_srt(audio_path, srt_path)
        self.refresh_pipeline_badges()

    def _on_video_rendered(self, output_path: str):
        """Khi video render xong ở tab 4, cập nhật lại trạng thái pipeline."""
        self.refresh_pipeline_badges()

    def _on_inner_tab_changed(self, index: int):
        """Khi bấm chuyển tab, tự động quét và cập nhật trạng thái."""
        if self.current_project:
            if index == 3:
                self.video_tab.auto_detect_defaults()
            self.refresh_pipeline_badges()

    def refresh_pipeline_badges(self):
        """Cập nhật trạng thái pipeline trực tiếp trên tên các tab."""
        if not self.current_project:
            return
        summary = self.current_project.get_pipeline_summary()

        clean_c = summary["clean_images_count"]
        raw_c = summary["raw_images_count"]
        if clean_c > 0:
            self.inner_tabs.setTabText(0, f"1  Ảnh ({clean_c}) ✓")
        elif raw_c > 0:
            self.inner_tabs.setTabText(0, f"1  Ảnh ({raw_c})")
        else:
            self.inner_tabs.setTabText(0, "1  Ảnh")

        if summary["voice_ready"]:
            self.inner_tabs.setTabText(1, "2  Giọng nói ✓")
        elif summary["has_voice"]:
            self.inner_tabs.setTabText(1, "2  Giọng nói ⚠")
        else:
            self.inner_tabs.setTabText(1, "2  Giọng nói")

        if summary["has_scenes"]:
            self.inner_tabs.setTabText(2, f"3  Kịch bản ({summary['scenes_count']}) ✓")
        else:
            self.inner_tabs.setTabText(2, "3  Kịch bản cảnh")

        vid_c = summary["videos_count"]
        if vid_c > 0:
            self.inner_tabs.setTabText(3, f"4  Dựng video ({vid_c}) ✓")
        else:
            self.inner_tabs.setTabText(3, "4  Dựng video")

    def save_project_manually(self, silent: bool = False):
        """Lưu lại toàn bộ dữ liệu hiện thời từ các tab vào dự án."""
        if not self.current_project:
            return

        # Lưu tab TTS
        if hasattr(self.tts_tab, "save_current_state"):
            self.tts_tab.save_current_state()

        # Lưu tab Kịch bản
        if hasattr(self.scene_tab, "save_current_state"):
            self.scene_tab.save_current_state()

        if not self.video_tab.save_current_state():
            return
        self.current_project.save_metadata()
        self.refresh_pipeline_badges()
        self.lbl_updated.setText(self._project_meta_text())
        if not silent:
            QMessageBox.information(
                self,
                "Đã lưu dự án",
                f"Đã lưu thành công toàn bộ dữ liệu và cấu hình cho dự án “{self.current_project.name}”."
            )

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
        self.scene_tab.set_project(None)
        self.video_tab.set_project(None)
        self.inner_tabs.setTabText(0, "1  Ảnh")
        self.inner_tabs.setTabText(1, "2  Giọng nói")
        self.inner_tabs.setTabText(2, "3  Kịch bản cảnh")
        self.inner_tabs.setTabText(3, "4  Dựng video")
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
            open_path(self.current_project.path)
        except OSError as exc:
            QMessageBox.warning(self, "Không thể mở thư mục", str(exc))

    @staticmethod
    def _format_updated_at(value: str) -> str:
        try:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y lúc %H:%M")
        except (TypeError, ValueError):
            return "không rõ"

    def _project_meta_text(self) -> str:
        if not self.current_project:
            return ""
        return (
            f"{self.current_project.aspect_ratio} · {self.current_project.fps} FPS · "
            f"Đã lưu {self._format_updated_at(self.current_project.updated_at)}"
        )

import json
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import config
from app.core import video_creator


class SceneTab(QWidget):
    """Bước nhập và kiểm tra kịch bản phân đoạn cảnh."""

    scene_path_changed = pyqtSignal(object)
    scenes_updated = pyqtSignal()

    TEXT_MODE = "text"
    FILE_MODE = "file"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("scene_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)
        self.project = None
        self._text_data = None
        self._valid_file_path = None
        self.auto_save: bool = False
        self._build_ui()

    def set_auto_save(self, enabled: bool):
        """Bật/tắt chế độ tự động lưu cho tab Kịch bản."""
        self.auto_save = enabled

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 18)
        root.setSpacing(12)

        title = QLabel("Kịch bản phân đoạn cảnh")
        title.setObjectName("page_title")
        root.addWidget(title)

        description = QLabel(
            "Nhập trực tiếp nội dung JSON hoặc chọn file có sẵn để ánh xạ ảnh với phụ đề."
        )
        description.setObjectName("meta_label")
        description.setWordWrap(True)
        root.addWidget(description)

        panel = QFrame()
        panel.setProperty("class", "panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(10)

        mode_label = QLabel("Cách nhập kịch bản")
        mode_label.setProperty("class", "section_label")
        panel_layout.addWidget(mode_label)

        self.combo_mode = QComboBox()
        self.combo_mode.addItem("Nhập nội dung JSON", self.TEXT_MODE)
        self.combo_mode.addItem("Chọn file JSON", self.FILE_MODE)
        self.combo_mode.currentIndexChanged.connect(self._on_mode_changed)
        panel_layout.addWidget(self.combo_mode)

        self.input_stack = QStackedWidget()

        text_page = QWidget()
        text_layout = QVBoxLayout(text_page)
        text_layout.setContentsMargins(0, 4, 0, 0)
        text_layout.setSpacing(8)
        text_label = QLabel("Nội dung JSON kịch bản phân đoạn cảnh")
        text_label.setProperty("class", "section_label")
        text_layout.addWidget(text_label)
        self.txt_scene_content = QPlainTextEdit()
        self.txt_scene_content.setPlaceholderText(
            """[
  {
    "id": "SC01",
    "character": "Người que",
    "character_info": "Nhân vật người que, đầu tròn, tay chân nét đơn theo ảnh tham chiếu.",
    "prompt": "",
    "subtitle_ids": [
      1,
      2
    ]
  },
  {
    "id": "SC02",
    "character": "",
    "character_info": "",
    "prompt": "Cận cảnh đống than trong hang đá",
    "subtitle_ids": [
      3
    ]
  }
]"""
        )
        self.txt_scene_content.setMinimumHeight(210)
        self.txt_scene_content.textChanged.connect(self._validate_text)
        text_layout.addWidget(self.txt_scene_content)
        self.input_stack.addWidget(text_page)

        file_page = QWidget()
        file_layout = QVBoxLayout(file_page)
        file_layout.setContentsMargins(0, 4, 0, 0)
        file_layout.setSpacing(8)
        file_label = QLabel("Đường dẫn file JSON kịch bản phân đoạn cảnh")
        file_label.setProperty("class", "section_label")
        file_layout.addWidget(file_label)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.txt_scene_path = QLineEdit()
        self.txt_scene_path.setPlaceholderText("Chọn hoặc nhập đường dẫn file scenes.json...")
        self.txt_scene_path.textChanged.connect(self._validate_file_path)
        path_row.addWidget(self.txt_scene_path, stretch=1)
        self.btn_browse = QPushButton("Chọn file...")
        self.btn_browse.clicked.connect(self.browse_scene_file)
        path_row.addWidget(self.btn_browse)
        file_layout.addLayout(path_row)
        file_layout.addStretch()
        self.input_stack.addWidget(file_page)

        panel_layout.addWidget(self.input_stack)

        self.lbl_status = QLabel("Chưa nhập kịch bản JSON.")
        self.lbl_status.setObjectName("meta_label")
        self.lbl_status.setWordWrap(True)
        panel_layout.addWidget(self.lbl_status)

        root.addWidget(panel, stretch=1)

    def set_project(self, project):
        self.project = project
        self._text_data = None
        self._valid_file_path = None
        self.combo_mode.setCurrentIndex(0)
        self.txt_scene_content.clear()
        self.txt_scene_path.clear()

        # Nạp lại kịch bản scenes.json đã có của dự án
        if project and project.scenes_path.exists():
            scenes_content = project.load_scenes_json()
            if scenes_content.strip():
                self.txt_scene_content.blockSignals(True)
                self.txt_scene_content.setPlainText(scenes_content)
                self.txt_scene_content.blockSignals(False)
                self._validate_text()
                if self._text_data:
                    self.scene_path_changed.emit(str(project.scenes_path.resolve()))
                    self.scenes_updated.emit()
                    return

        self._set_status("Chưa nhập kịch bản JSON.", False)
        self.scene_path_changed.emit("")
        self.scenes_updated.emit()

    def browse_scene_file(self):
        current = self.txt_scene_path.text().strip().strip('"')
        initial_dir = str(Path(current).parent) if current else str(config.DOWNLOADS_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file JSON kịch bản phân đoạn cảnh",
            initial_dir,
            "JSON Files (*.json);;All Files (*.*)",
        )
        if path:
            self.txt_scene_path.setText(str(Path(path).resolve()))

    def _on_mode_changed(self, index: int):
        self.input_stack.setCurrentIndex(index)
        self.scene_path_changed.emit("")
        if self.combo_mode.currentData() == self.TEXT_MODE:
            self._validate_text()
        else:
            self._validate_file_path(self.txt_scene_path.text())

    def _validate_text(self):
        content = self.txt_scene_content.toPlainText().strip()
        self._text_data = None
        if not content:
            self._set_status("Chưa nhập nội dung JSON.", False)
            self.scene_path_changed.emit("")
            self.scenes_updated.emit()
            return
        try:
            data = json.loads(content)
            scenes = video_creator.parse_json_data(data, [])
            if not scenes:
                self._set_status("JSON hợp lệ nhưng chưa có phân cảnh.", False)
                self.scene_path_changed.emit("")
            else:
                self._text_data = data
                self._set_status(f"✓ Đã nhận diện {len(scenes)} phân cảnh từ nội dung JSON.", True)
                if self.auto_save and self.project:
                    try:
                        self.project.scenes_path.write_text(
                            json.dumps(self._text_data, ensure_ascii=False, indent=2),
                            encoding="utf-8"
                        )
                        self.project.save_metadata()
                    except Exception:
                        pass
                self.scene_path_changed.emit(data)
                self.scenes_updated.emit()
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            self._set_status(f"JSON không hợp lệ: {exc}", False)
            self.scene_path_changed.emit("")
            self.scenes_updated.emit()

    def _validate_file_path(self, value: str):
        clean_value = value.strip().strip('"')
        path = Path(clean_value) if clean_value else None
        self._valid_file_path = None
        valid = False
        message = "Chưa chọn file JSON."

        if path:
            if not path.is_file():
                message = "Không tìm thấy file tại đường dẫn đã nhập."
            elif path.suffix.lower() != ".json":
                message = "File kịch bản phải có định dạng .json."
            else:
                try:
                    scenes = video_creator.parse_json_mapping(path, [])
                    if not scenes:
                        message = "JSON hợp lệ nhưng chưa có phân cảnh."
                    else:
                        valid = True
                        self._valid_file_path = path.resolve()
                        message = f"Đã nhận diện {len(scenes)} phân cảnh · {path.name}"
                except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
                    message = f"JSON không hợp lệ: {exc}"

        if self.combo_mode.currentData() == self.FILE_MODE:
            self._set_status(message, valid)
            self.scene_path_changed.emit(str(self._valid_file_path) if valid else "")

    def _set_status(self, message: str, valid: bool):
        self.lbl_status.setText(message)
        self.lbl_status.setObjectName("meta_label" if valid else "field_error")
        self.lbl_status.style().unpolish(self.lbl_status)
        self.lbl_status.style().polish(self.lbl_status)

    def dragEnterEvent(self, event: QDragEnterEvent):
        urls = event.mimeData().urls() if event.mimeData().hasUrls() else []
        if any(Path(url.toLocalFile()).suffix.lower() == ".json" for url in urls):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_file() and path.suffix.lower() == ".json":
                self.combo_mode.setCurrentIndex(1)
                self.txt_scene_path.setText(str(path.resolve()))
                event.acceptProposedAction()
                return

    def save_current_state(self):
        """Lưu lại nội dung kịch bản hiện tại vào scenes.json của dự án."""
        if not self.project:
            return
        if self.combo_mode.currentData() == self.TEXT_MODE and self._text_data is not None:
            self.project.save_scenes_json(json.dumps(self._text_data, ensure_ascii=False, indent=2))
        elif self._valid_file_path and self._valid_file_path.exists():
            try:
                content = self._valid_file_path.read_text(encoding="utf-8")
                self.project.save_scenes_json(content)
            except Exception:
                pass

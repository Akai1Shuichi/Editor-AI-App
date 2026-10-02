from pathlib import Path
from copy import deepcopy
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QSize, QSignalBlocker
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor, QIcon, QPainter, QPen, QImageReader
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QProgressBar, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QSplitter, QScrollArea, QApplication, QSizePolicy, QTreeWidget,
    QTreeWidgetItem, QSlider, QToolButton, QTabWidget
)

from app import config
from app.core import edit_document, video_creator
from app.core.platform_utils import open_path
from app.ui.widgets import ToggleSwitch


class VideoRenderWorker(QThread):
    """Worker chạy tiến trình FFmpeg ghép video ngầm trên luồng riêng."""
    progress_updated = pyqtSignal(int, str)
    render_finished = pyqtSignal(bool, dict)

    def __init__(
        self,
        timeline: List[Dict[str, Any]],
        audio_path: Path,
        output_path: Path,
        total_audio_duration: float,
        aspect_ratio: str = "16:9",
        fps: int = 30,
        subtitles: Optional[List[Dict[str, Any]]] = None,
    ):
        super().__init__()
        self.timeline = timeline
        self.audio_path = audio_path
        self.output_path = output_path
        self.total_audio_duration = total_audio_duration
        self.aspect_ratio = aspect_ratio
        self.fps = fps
        self.subtitles = subtitles
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        def on_prog(pct: int, msg: str):
            self.progress_updated.emit(pct, msg)

        render_options = dict(
            timeline=self.timeline,
            audio_path=self.audio_path,
            output_path=self.output_path,
            total_audio_duration=self.total_audio_duration,
            aspect_ratio=self.aspect_ratio,
            fps=self.fps,
            progress_callback=on_prog,
            is_cancelled=lambda: self._is_cancelled
        )
        if self.subtitles is not None:
            render_options["subtitles"] = self.subtitles
        try:
            res = video_creator.render_video(**render_options)
        except Exception as exc:
            res = {"success": False, "error": str(exc)}
        self.render_finished.emit(res.get("success", False), res)


class PreviewImage(QLabel):
    """Show the same centered cover crop and aspect ratio as the export."""

    def __init__(self):
        super().__init__("Chọn một cảnh trên timeline để xem ảnh")
        self._source = QPixmap()
        self._gap = False
        self._aspect_ratio = 16 / 9
        self._placeholder = "Chọn một cảnh trên timeline để xem ảnh"
        self.setObjectName("video_preview_canvas")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(190)
        self.setWordWrap(True)
        overlay_layout = QVBoxLayout(self)
        overlay_layout.setContentsMargins(18, 8, 18, 14)
        overlay_layout.addStretch()
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("video_preview_subtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setTextFormat(Qt.TextFormat.PlainText)
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.hide()
        overlay_layout.addWidget(self.subtitle_label)

    def set_aspect_ratio(self, value: str):
        self._aspect_ratio = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1}.get(value, 16 / 9)
        self._update_pixmap()

    def set_subtitle(self, text: str):
        if self.subtitle_label.text() == text:
            return
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def set_image(self, path: Optional[Path]):
        self._gap = False
        self._source = QPixmap(str(path)) if path and path.is_file() else QPixmap()
        self._placeholder = ("Không tìm thấy hoặc không đọc được ảnh cảnh" if path else
                             "Chọn một cảnh trên timeline để xem ảnh")
        self._update_pixmap()

    def show_gap(self):
        self._gap = True
        self._source = QPixmap()
        self._update_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmap()

    def _update_pixmap(self):
        if self._gap and self.width() > 0 and self.height() > 0:
            canvas = QPixmap(self.size())
            canvas.fill(QColor("#000000"))
            self.setPixmap(canvas)
        elif not self._source.isNull() and self.width() > 0 and self.height() > 0:
            frame_width = min(self.width(), round(self.height() * self._aspect_ratio))
            frame_height = min(self.height(), round(self.width() / self._aspect_ratio))
            frame_width = max(1, frame_width)
            frame_height = max(1, frame_height)
            scaled = self._source.scaled(
                frame_width, frame_height, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            crop = scaled.copy((scaled.width() - frame_width) // 2,
                               (scaled.height() - frame_height) // 2,
                               frame_width, frame_height)
            canvas = QPixmap(self.size())
            canvas.fill(QColor("#000000"))
            painter = QPainter(canvas)
            painter.drawPixmap((self.width() - frame_width) // 2,
                               (self.height() - frame_height) // 2, crop)
            painter.end()
            self.setPixmap(canvas)
            x_margin = (self.width() - frame_width) // 2
            bottom_margin = (self.height() - frame_height) // 2
            self.layout().setContentsMargins(x_margin + 12, 8, x_margin + 12,
                                             bottom_margin + 12)
            self.subtitle_label.setStyleSheet(
                f"font-size: {max(9, round(frame_height * 0.039))}px;"
            )
        else:
            self.clear()
            self.setText(self._placeholder)


class TimeRuler(QWidget):
    """Paint a time ruler and let users seek at its exact timeline position."""

    seek_requested = pyqtSignal(int)
    PIXELS_PER_SECOND = 65
    TRACK_OFFSET = 58

    def __init__(self):
        super().__init__()
        self.duration = 0.0
        self.position = 0.0
        self.setFixedHeight(27)
        self.setMinimumWidth(self.TRACK_OFFSET + 1)
        self.setMouseTracking(True)

    def set_duration(self, duration: float):
        self.duration = max(0.0, duration)
        self.setMinimumWidth(self.TRACK_OFFSET + round(self.duration * self.PIXELS_PER_SECOND))
        self.update()

    def set_position(self, position: float):
        self.position = position
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#171b24"))
        painter.setPen(QPen(QColor("#64748b")))
        painter.drawText(4, 20, "GIÂY")
        if self.duration <= 0:
            return
        interval = next((step for step in (1, 2, 5, 10, 15, 30, 60, 120, 300, 600)
                         if step * self.PIXELS_PER_SECOND >= 62), 600)
        tick = 0
        while tick <= self.duration:
            x = self.TRACK_OFFSET + round(tick * self.PIXELS_PER_SECOND)
            painter.drawLine(x, 19, x, 30)
            painter.drawText(x + 3, 15, video_creator.format_time(tick).split(".")[0])
            tick += interval
        x = self.TRACK_OFFSET + round(self.position * self.PIXELS_PER_SECOND)
        painter.setPen(QPen(QColor("#7397ec"), 2))
        painter.drawLine(x, 0, x, self.height())

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._seek_at(event.position().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._seek_at(event.position().x())

    def _seek_at(self, x: float):
        position = max(0.0, min(self.duration, (x - self.TRACK_OFFSET) / self.PIXELS_PER_SECOND))
        self.seek_requested.emit(round(position * 1000))


class VideoTab(QWidget):
    """Tab Ghép Video Tự Động từ Ảnh, Voice, Phụ đề SRT & Kịch bản JSON."""

    video_rendered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("video_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        self.worker: Optional[VideoRenderWorker] = None
        self.current_timeline: List[Dict[str, Any]] = []
        self.total_audio_duration: float = 0.0
        self.last_output_video: Optional[Path] = None
        self.project = None
        self._json_data = None
        self.edit_document: Optional[Dict[str, Any]] = None
        self.auto_save = False
        self._loading_edit = False
        self._edit_dirty = False
        self._selected_scene = None
        self._preview_subtitles = []
        self._preview_audio_path = None
        self._playhead_ms = 0
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        self.init_ui()
        self.player.positionChanged.connect(self._on_player_position_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.errorOccurred.connect(self._on_preview_error)
        self.combo_ratio.currentIndexChanged.connect(self._on_export_settings_changed)
        self.combo_fps.currentIndexChanged.connect(self._on_export_settings_changed)
        self.chk_subtitles.toggled.connect(self._on_export_settings_changed)
        self.auto_detect_defaults()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(10)

        def title(text):
            label = QLabel(text)
            label.setObjectName("video_section_title")
            return label

        def field(layout, label, widget):
            caption = QLabel(label)
            caption.setObjectName("video_field_label")
            layout.addWidget(caption)
            layout.addWidget(widget)

        def scroll_page(widget):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(widget)
            return scroll

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        heading = QLabel("Dựng video")
        heading.setObjectName("video_workspace_title")
        toolbar.addWidget(heading)
        toolbar.addStretch()
        self.btn_sources = QPushButton("Nguồn")
        self.btn_sources.setObjectName("video_panel_toggle")
        self.btn_sources.setCheckable(True)
        self.btn_sources.setToolTip("Mở hoặc thu gọn thư viện và tệp nguồn")
        toolbar.addWidget(self.btn_sources)
        self.btn_properties = QPushButton("Thuộc tính")
        self.btn_properties.setObjectName("video_panel_toggle")
        self.btn_properties.setCheckable(True)
        self.btn_properties.setToolTip("Mở hoặc thu gọn thuộc tính cảnh và cấu hình xuất")
        toolbar.addWidget(self.btn_properties)
        self.btn_export_settings = QPushButton("Xuất video")
        self.btn_export_settings.setObjectName("btn_primary")
        self.btn_export_settings.clicked.connect(self._open_export_settings)
        toolbar.addWidget(self.btn_export_settings)
        main_layout.addLayout(toolbar)

        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setObjectName("video_workspace_splitter")
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.setHandleWidth(5)

        library_page = QWidget()
        library_page.setObjectName("video_library_page")
        library_layout = QVBoxLayout(library_page)
        library_layout.setContentsMargins(12, 12, 12, 12)
        library_layout.setSpacing(10)
        library_layout.addWidget(title("Thư viện"))
        self.lbl_project_badge = QLabel("Chưa chọn dự án")
        self.lbl_project_badge.setObjectName("video_muted")
        self.lbl_project_badge.setWordWrap(True)
        library_layout.addWidget(self.lbl_project_badge)
        self.asset_tree = QTreeWidget()
        self.asset_tree.setObjectName("video_asset_tree")
        self.asset_tree.setHeaderHidden(True)
        self.asset_tree.setIconSize(QSize(40, 32))
        self.asset_tree.setMinimumHeight(140)
        self.asset_tree.setIndentation(14)
        self.asset_tree.setUniformRowHeights(True)
        self.asset_tree.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.asset_tree.itemClicked.connect(self._on_asset_clicked)
        library_layout.addWidget(self.asset_tree, stretch=1)
        self.lbl_asset_hint = QLabel("Chọn ảnh để xem trước")
        self.lbl_asset_hint.setObjectName("video_muted")
        library_layout.addWidget(self.lbl_asset_hint)

        self.btn_edit_sources = QToolButton()
        self.btn_edit_sources.setObjectName("video_source_disclosure")
        self.btn_edit_sources.setText("Đổi tệp nguồn")
        self.btn_edit_sources.setCheckable(True)
        self.btn_edit_sources.setArrowType(Qt.ArrowType.RightArrow)
        self.btn_edit_sources.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        library_layout.addWidget(self.btn_edit_sources)
        self.source_fields = QWidget()
        source_layout = QVBoxLayout(self.source_fields)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.setSpacing(6)
        for attribute, caption, placeholder, callback in (
            ("txt_image_dir", "Thư mục ảnh", "Chọn thư mục ảnh", self.browse_image_dir),
            ("txt_audio_file", "Voice", "Chọn file âm thanh", self.browse_audio_file),
            ("txt_srt_file", "Phụ đề SRT", "Chọn file SRT", self.browse_srt_file),
        ):
            label = QLabel(caption)
            label.setObjectName("video_field_label")
            source_layout.addWidget(label)
            row = QHBoxLayout()
            row.setSpacing(5)
            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setMinimumWidth(0)
            edit.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            edit.textChanged.connect(self.on_input_changed)
            setattr(self, attribute, edit)
            browse = QPushButton("Chọn")
            browse.setObjectName("video_browse_button")
            browse.clicked.connect(callback)
            row.addWidget(edit, stretch=1)
            row.addWidget(browse)
            source_layout.addLayout(row)
        self.txt_json_file = QLineEdit(self)
        self.txt_json_file.hide()
        self.txt_json_file.textChanged.connect(self.on_input_changed)
        self.source_fields.hide()
        self.btn_edit_sources.toggled.connect(self.source_fields.setVisible)
        self.btn_edit_sources.toggled.connect(lambda expanded: self.btn_edit_sources.setArrowType(
            Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow))
        library_layout.addWidget(self.source_fields)
        self.btn_preview = QPushButton("Tạo timeline")
        self.btn_preview.setObjectName("btn_subtle")
        self.btn_preview.clicked.connect(self.analyze_timeline)
        library_layout.addWidget(self.btn_preview)
        self.btn_rebuild = QPushButton("Tạo lại từ nguồn")
        self.btn_rebuild.setObjectName("video_text_button")
        self.btn_rebuild.setToolTip("Tạo lại bản dựng từ tệp nguồn; bản cũ được sao lưu")
        self.btn_rebuild.clicked.connect(self.rebuild_timeline)
        self.btn_rebuild.hide()
        library_layout.addWidget(self.btn_rebuild)
        self.source_panel = scroll_page(library_page)
        self.source_panel.setObjectName("video_source_panel")
        self.source_panel.setMinimumWidth(210)
        self.source_panel.setMaximumWidth(290)
        self.workspace_splitter.addWidget(self.source_panel)

        preview_panel = QFrame()
        preview_panel.setObjectName("video_preview_panel")
        preview_panel.setMinimumWidth(260)
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(12, 10, 12, 10)
        preview_layout.setSpacing(10)
        preview_layout.addWidget(title("Xem trước"))
        self.preview_image = PreviewImage()
        self.preview_image.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.preview_image.setMinimumHeight(80)
        preview_layout.addWidget(self.preview_image, stretch=1)
        transport = QHBoxLayout()
        transport.setSpacing(10)
        self.btn_play_pause = QPushButton("▶ Phát voice")
        self.btn_play_pause.setObjectName("video_transport_button")
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self.toggle_preview_playback)
        transport.addWidget(self.btn_play_pause)
        self.slider_playhead = QSlider(Qt.Orientation.Horizontal)
        self.slider_playhead.setObjectName("video_playhead_slider")
        self.slider_playhead.setRange(0, 0)
        self.slider_playhead.valueChanged.connect(self.seek_preview)
        transport.addWidget(self.slider_playhead, stretch=1)
        preview_layout.addLayout(transport)
        self.lbl_preview_time = QLabel("00:00.000 / 00:00.000")
        self.lbl_preview_time.setObjectName("video_timecode")
        self.lbl_preview_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview_time.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        preview_layout.addWidget(self.lbl_preview_time)
        self.workspace_splitter.addWidget(preview_panel)

        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.setObjectName("video_inspector_tabs")
        self.inspector_tabs.setDocumentMode(True)
        self.inspector_tabs.tabBar().setDrawBase(False)
        self.inspector_tabs.setMinimumWidth(230)
        self.inspector_tabs.setMaximumWidth(300)
        inspector = QWidget()
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(14, 14, 14, 14)
        inspector_layout.setSpacing(10)
        self.lbl_clip_name = QLabel("Chọn một cảnh")
        self.lbl_clip_name.setObjectName("video_clip_name")
        inspector_layout.addWidget(self.lbl_clip_name)
        self.lbl_clip_range = QLabel("Thời gian: —")
        self.lbl_clip_range.setObjectName("video_muted")
        self.lbl_clip_range.setWordWrap(True)
        inspector_layout.addWidget(self.lbl_clip_range)
        inspector_layout.addWidget(title("Ảnh cảnh"))
        self.lbl_clip_media = QLabel("Ảnh: —")
        self.lbl_clip_media.setWordWrap(True)
        self.lbl_clip_media.setMinimumWidth(0)
        inspector_layout.addWidget(self.lbl_clip_media)
        self.lbl_clip_image_status = QLabel("Trạng thái ảnh: —")
        self.lbl_clip_image_status.setObjectName("video_clip_image_status")
        self.lbl_clip_image_status.setWordWrap(True)
        self.lbl_clip_image_status.setMinimumWidth(0)
        inspector_layout.addWidget(self.lbl_clip_image_status)
        self.btn_replace_scene_image = QPushButton("Thay ảnh…")
        self.btn_replace_scene_image.setObjectName("btn_subtle")
        self.btn_replace_scene_image.setEnabled(False)
        self.btn_replace_scene_image.clicked.connect(self.choose_scene_image)
        inspector_layout.addWidget(self.btn_replace_scene_image)
        self.txt_clip_image_path = QLineEdit()
        self.txt_clip_image_path.setObjectName("video_clip_image_path")
        self.txt_clip_image_path.setReadOnly(True)
        self.txt_clip_image_path.setMinimumWidth(0)
        self.txt_clip_image_path.setPlaceholderText("Đường dẫn ảnh")
        self.txt_clip_image_path.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        inspector_layout.addWidget(self.txt_clip_image_path)
        self.lbl_clip_motion = QLabel("Chuyển động: —")
        self.lbl_clip_motion.setObjectName("video_muted")
        inspector_layout.addWidget(self.lbl_clip_motion)
        inspector_layout.addWidget(title("Nội dung phụ đề"))
        self.lbl_clip_subtitles = QLabel("Phụ đề: —")
        self.lbl_clip_subtitles.setWordWrap(True)
        self.lbl_clip_subtitles.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_clip_subtitles.setMinimumWidth(0)
        self.lbl_clip_subtitles.setObjectName("video_caption_content")
        inspector_layout.addWidget(self.lbl_clip_subtitles)
        inspector_layout.addStretch()
        self.inspector_tabs.addTab(scroll_page(inspector), "Cảnh")

        export_page = QWidget()
        export_layout = QVBoxLayout(export_page)
        export_layout.setContentsMargins(14, 14, 14, 14)
        export_layout.setSpacing(10)
        self.combo_ratio = QComboBox()
        self.combo_ratio.addItem("16:9 · Ngang", "16:9")
        self.combo_ratio.addItem("9:16 · Dọc", "9:16")
        self.combo_ratio.addItem("1:1 · Vuông", "1:1")
        self.combo_fps = QComboBox()
        self.combo_fps.addItem("30 FPS", 30)
        self.combo_fps.addItem("60 FPS", 60)
        self.combo_fps.addItem("24 FPS", 24)
        format_row = QHBoxLayout()
        format_row.setSpacing(8)
        for label, combo in (("Khung hình", self.combo_ratio), ("FPS", self.combo_fps)):
            combo.setMinimumWidth(0)
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            column = QVBoxLayout()
            column.setSpacing(6)
            field(column, label, combo)
            format_row.addLayout(column, stretch=1)
        export_layout.addLayout(format_row)
        subtitle_row = QHBoxLayout()
        subtitle_row.addWidget(QLabel("Phụ đề trên video"))
        subtitle_row.addStretch()
        self.chk_subtitles = ToggleSwitch()
        self.chk_subtitles.setAccessibleName("Bật phụ đề trên video")
        self.chk_subtitles.setChecked(False)
        self.chk_subtitles.setToolTip("Hiện phụ đề trong preview và video xuất. Mặc định tắt.")
        subtitle_row.addWidget(self.chk_subtitles)
        export_layout.addLayout(subtitle_row)
        subtitle_hint = QLabel("Áp dụng cho preview và video xuất")
        subtitle_hint.setObjectName("video_muted")
        subtitle_hint.setWordWrap(True)
        export_layout.addWidget(subtitle_hint)
        self.txt_output_path = QLineEdit()
        self.txt_output_path.setMinimumWidth(0)
        self.txt_output_path.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.txt_output_path.setPlaceholderText("Đường dẫn file .mp4")
        self.txt_output_path.textChanged.connect(self.txt_output_path.setToolTip)
        output_label = QLabel("Lưu video tại")
        output_label.setObjectName("video_field_label")
        export_layout.addWidget(output_label)
        output_row = QHBoxLayout()
        output_row.setSpacing(5)
        output_row.addWidget(self.txt_output_path, stretch=1)
        browse_output = QPushButton("Chọn")
        browse_output.setObjectName("video_browse_button")
        browse_output.setToolTip("Chọn tên file và thư mục lưu video")
        browse_output.clicked.connect(self.browse_output_file)
        output_row.addWidget(browse_output)
        export_layout.addLayout(output_row)
        export_hint = QLabel("MP4 · H.264 / AAC")
        export_hint.setObjectName("video_muted")
        self.btn_start = QPushButton("Xuất MP4")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setMinimumHeight(36)
        self.btn_start.clicked.connect(self.start_render)
        export_layout.addStretch()
        export_container = QWidget()
        export_container_layout = QVBoxLayout(export_container)
        export_container_layout.setContentsMargins(0, 0, 0, 0)
        export_container_layout.setSpacing(0)
        export_container_layout.addWidget(scroll_page(export_page), stretch=1)
        export_footer = QWidget()
        export_footer_layout = QVBoxLayout(export_footer)
        export_footer_layout.setContentsMargins(14, 8, 14, 12)
        export_footer_layout.setSpacing(6)
        export_footer_layout.addWidget(export_hint)
        export_footer_layout.addWidget(self.btn_start)
        export_container_layout.addWidget(export_footer)
        self.inspector_tabs.addTab(export_container, "Xuất video")
        self.workspace_splitter.addWidget(self.inspector_tabs)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setStretchFactor(2, 0)
        self.workspace_splitter.setSizes([240, 640, 260])
        self.btn_sources.toggled.connect(self._toggle_source_panel)
        self.btn_properties.toggled.connect(self._toggle_inspector_panel)
        self.btn_sources.setChecked(True)
        self.btn_properties.setChecked(True)
        self._layout_mode = None

        timeline_panel = QWidget()
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(7)
        summary = QHBoxLayout()
        summary.setSpacing(16)
        summary.addWidget(title("Timeline"))
        self.lbl_summary_scenes = QLabel("0 cảnh")
        self.lbl_summary_duration = QLabel("00:00.000")
        self.lbl_summary_images = QLabel("Chưa có bản dựng")
        for label in (self.lbl_summary_scenes, self.lbl_summary_duration, self.lbl_summary_images):
            label.setObjectName("video_timeline_meta")
            summary.addWidget(label)
        summary.addStretch()
        timeline_layout.addLayout(summary)
        self.timeline_views = QTabWidget()
        self.timeline_views.setObjectName("video_timeline_views")
        self.timeline_views.setDocumentMode(True)
        self.timeline_views.tabBar().setDrawBase(False)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setObjectName("video_timeline_scroll")
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.timeline_content = QWidget()
        self.timeline_lanes = QVBoxLayout(self.timeline_content)
        self.timeline_lanes.setContentsMargins(8, 8, 8, 8)
        self.timeline_lanes.setSpacing(4)
        self.time_ruler = TimeRuler()
        self.time_ruler.seek_requested.connect(self.seek_preview)
        self.timeline_scroll.setWidget(self.timeline_content)
        self.timeline_views.addTab(self.timeline_scroll, "Dải thời gian")
        self.table = QTableWidget()
        self.table.setObjectName("video_scene_table")
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["#", "Cảnh", "Phụ đề", "Ảnh", "Bắt đầu", "Kết thúc", "Độ dài"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for column, width in ((0, 36), (1, 76), (2, 76), (4, 88), (5, 88), (6, 72)):
            self.table.setColumnWidth(column, width)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(32)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self.on_table_row_clicked)
        self.timeline_views.addTab(self.table, "Danh sách cảnh")
        timeline_layout.addWidget(self.timeline_views, stretch=1)
        self.editor_splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor_splitter.setChildrenCollapsible(False)
        self.editor_splitter.setHandleWidth(5)
        self.editor_splitter.addWidget(self.workspace_splitter)
        self.editor_splitter.addWidget(timeline_panel)
        timeline_panel.setMinimumHeight(140)
        self.editor_splitter.setStretchFactor(0, 3)
        self.editor_splitter.setStretchFactor(1, 1)
        self.editor_splitter.setSizes([430, 205])
        main_layout.addWidget(self.editor_splitter, stretch=1)

        self.panel_result = QFrame()
        self.panel_result.setObjectName("video_result_bar")
        result_layout = QHBoxLayout(self.panel_result)
        result_layout.setContentsMargins(10, 8, 10, 8)
        result_layout.setSpacing(8)
        self.lbl_res_details = QLabel()
        self.lbl_res_details.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_res_details.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        result_layout.addWidget(self.lbl_res_details, stretch=1)
        self.btn_open_video = QPushButton("Mở video")
        self.btn_open_video.setObjectName("btn_subtle")
        self.btn_open_video.clicked.connect(self.open_video_file)
        self.btn_open_dir = QPushButton("Thư mục")
        self.btn_open_dir.setObjectName("btn_subtle")
        self.btn_open_dir.clicked.connect(self.open_output_dir)
        self.btn_copy_path = QPushButton("Sao chép")
        self.btn_copy_path.setObjectName("btn_subtle")
        self.btn_copy_path.clicked.connect(self.copy_output_path)
        for button in (self.btn_open_video, self.btn_open_dir, self.btn_copy_path):
            result_layout.addWidget(button)
        self.panel_result.hide()
        main_layout.addWidget(self.panel_result)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)
        status_row = QHBoxLayout()
        self.lbl_status = QLabel("Chọn nguồn và tạo timeline để bắt đầu.")
        self.lbl_status.setObjectName("video_status")
        self.lbl_status.setTextFormat(Qt.TextFormat.PlainText)
        self.lbl_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setMaximumHeight(34)
        status_row.addWidget(self.lbl_status, stretch=1)
        self.btn_cancel = QPushButton("Hủy xuất")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.hide()
        self.btn_cancel.clicked.connect(self.cancel_render)
        status_row.addWidget(self.btn_cancel)
        main_layout.addLayout(status_row)
        self._refresh_asset_library()
        self._refresh_timeline_tracks()

    def _open_export_settings(self):
        self.btn_properties.setChecked(True)
        self.inspector_tabs.setCurrentIndex(1)

    def _toggle_source_panel(self, visible):
        if visible and self.width() < 850:
            self.btn_properties.setChecked(False)
        self.source_panel.setVisible(visible)

    def _toggle_inspector_panel(self, visible):
        if visible and self.width() < 850:
            self.btn_sources.setChecked(False)
        self.inspector_tabs.setVisible(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        mode = 0 if self.width() < 700 else 1 if self.width() < 1000 else 2
        if mode != self._layout_mode:
            self._layout_mode = mode
            self.btn_sources.setChecked(mode == 2)
            self.btn_properties.setChecked(mode > 0)

    def _refresh_asset_library(self):
        """Show the files currently chosen as sources without altering the saved edit."""
        self.asset_tree.clear()
        image_group = QTreeWidgetItem(["Ảnh cảnh"])
        voice_group = QTreeWidgetItem(["Voice"])
        subtitle_group = QTreeWidgetItem(["Phụ đề"])
        script_group = QTreeWidgetItem(["Kịch bản"])
        for group in (image_group, voice_group, subtitle_group, script_group):
            self.asset_tree.addTopLevelItem(group)

        image_dir_text = self.txt_image_dir.text().strip().strip('"')
        image_dir = Path(image_dir_text) if image_dir_text else None
        image_files = []
        if image_dir and image_dir.is_dir():
            image_files = sorted(
                (path for path in image_dir.iterdir() if path.is_file() and
                 path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}),
                key=lambda path: path.name.casefold(),
            )
        for path in image_files:
            item = QTreeWidgetItem([path.name])
            item.setIcon(0, QIcon(str(path)))
            item.setData(0, Qt.ItemDataRole.UserRole, ("image", str(path)))
            item.setToolTip(0, str(path))
            image_group.addChild(item)
        image_group.setText(0, f"Ảnh cảnh ({len(image_files)})")
        self.lbl_asset_hint.setText("Chọn ảnh để xem trước" if image_files else "Mở 'Đổi tệp nguồn' để chọn ảnh")
        self.lbl_asset_hint.setWordWrap(True)

        for group, kind, line_edit in (
            (voice_group, "audio", self.txt_audio_file),
            (subtitle_group, "srt", self.txt_srt_file),
            (script_group, "script", self.txt_json_file),
        ):
            selected = line_edit.text().strip().strip('"')
            if selected:
                path = Path(selected)
                item = QTreeWidgetItem([path.name or selected])
                item.setData(0, Qt.ItemDataRole.UserRole, (kind, str(path)))
                item.setToolTip(0, str(path))
                group.addChild(item)
            elif kind == "script" and self._json_data is not None:
                group.addChild(QTreeWidgetItem(["Kịch bản từ Bước 3"]))
        self.asset_tree.expandAll()

    def _on_asset_clicked(self, item, _column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, location = data
        if kind == "image":
            if self.inspector_tabs.isVisible():
                self.inspector_tabs.setCurrentIndex(0)
            self._selected_scene = None
            self.table.clearSelection()
            self.preview_image.set_image(Path(location))
            self.preview_image.set_subtitle("")
            self.lbl_preview_time.setText(f"Asset: {Path(location).name}")
            self.lbl_clip_name.setText("Ảnh trong thư viện")
            self.lbl_clip_media.setText(Path(location).name)
            self.lbl_clip_media.setToolTip(location)
            status, valid = self._image_status(Path(location))
            self.lbl_clip_image_status.setText(status)
            self.lbl_clip_image_status.setProperty("valid", valid)
            self.lbl_clip_image_status.style().unpolish(self.lbl_clip_image_status)
            self.lbl_clip_image_status.style().polish(self.lbl_clip_image_status)
            self.txt_clip_image_path.setText(location)
            self.btn_replace_scene_image.setEnabled(False)
            self.lbl_clip_range.setText("Thời gian: Chưa gán cảnh")
            self.lbl_clip_motion.setText("Chuyển động: —")
            self.lbl_clip_subtitles.setText("Phụ đề: —")
            for button in self._scene_buttons:
                button.setProperty("selected", False)
                button.style().unpolish(button)
                button.style().polish(button)
        else:
            self.lbl_status.setText(f"{item.text(0)} · {location}")

    @staticmethod
    def _image_status(path: Optional[Path]):
        if path is None:
            return "Chưa gán ảnh", False
        if not path.is_file():
            return "Thiếu tệp ảnh", False
        reader = QImageReader(str(path))
        if not reader.canRead():
            return "Không đọc được ảnh", False
        size = reader.size()
        if size.isValid():
            return f"Sẵn sàng · {size.width()} × {size.height()} px", True
        return "Sẵn sàng", True

    def _refresh_timeline_tracks(self):
        while self.timeline_lanes.count():
            entry = self.timeline_lanes.takeAt(0)
            if entry.widget() and entry.widget() is not self.time_ruler:
                entry.widget().deleteLater()
        self._scene_buttons = []
        self.time_ruler.set_duration(self.total_audio_duration if self.current_timeline else 0)
        self.timeline_lanes.addWidget(self.time_ruler)
        self.timeline_content.setMinimumWidth(self.time_ruler.minimumWidth() + 8)

        def lane(title, *, spacing=3):
            widget = QWidget()
            row = QHBoxLayout(widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(spacing)
            label = QLabel(title)
            label.setFixedWidth(58)
            label.setProperty("class", "section_label")
            row.addWidget(label)
            self.timeline_lanes.addWidget(widget)
            return row

        video_row = lane("ẢNH", spacing=0)
        if self.current_timeline:
            video_track = QWidget()
            video_track.setFixedSize(
                max(1, round(self.total_audio_duration * self.time_ruler.PIXELS_PER_SECOND)), 48
            )
            video_row.addWidget(video_track)
            for index, clip in enumerate(self.current_timeline):
                width = max(1, round(clip["duration"] * self.time_ruler.PIXELS_PER_SECOND))
                button = QPushButton(clip["id"] if width >= 70 else "", video_track)
                button.setObjectName("video_timeline_clip")
                button.setToolTip(f"{video_creator.format_time(clip['start'])} – "
                                  f"{video_creator.format_time(clip['end'])} · {clip['id']}")
                button.setFixedWidth(width)
                button.setFixedHeight(48)
                button.move(round(clip["start"] * self.time_ruler.PIXELS_PER_SECOND), 0)
                image = clip.get("image")
                if image and image.is_file():
                    thumbnail = QPixmap(str(image))
                    if not thumbnail.isNull():
                        button.setIcon(QIcon(thumbnail))
                        button.setIconSize(QSize(max(1, min(52, width - 8)), 37))
                button.clicked.connect(lambda _checked=False, row=index: self._select_scene(row))
                self._scene_buttons.append(button)
        else:
            video_row.addWidget(QLabel("Chưa có timeline. Phân tích nguồn để bắt đầu."))
        video_row.addStretch()

        voice_row = lane("VOICE")
        voice_ref = (self.edit_document["tracks"]["audio"][0]["media"]
                     if self.edit_document else self.txt_audio_file.text())
        voice_name = Path(voice_ref).name if voice_ref else "Chưa chọn voice"
        voice_row.addWidget(QLabel(f"{voice_name}  ·  {self.total_audio_duration:.1f}s"))
        voice_row.addStretch()

        subtitle_row = lane("SRT")
        if self.edit_document:
            count = len(self.edit_document["tracks"]["subtitles"])
            subtitle_row.addWidget(QLabel(f"{count} đoạn phụ đề trong bản dựng"))
        else:
            subtitle_row.addWidget(QLabel("Phụ đề sẽ hiện sau khi tạo timeline"))
        subtitle_row.addStretch()

    def _select_scene(self, row: int, *, seek: bool = True):
        if not 0 <= row < len(self.current_timeline):
            return
        if seek:
            if self.inspector_tabs.isVisible():
                self.inspector_tabs.setCurrentIndex(0)
            self.seek_preview(round(self.current_timeline[row]["start"] * 1000))
            return
        self._selected_scene = row
        clip = self.current_timeline[row]
        self.table.selectRow(row)
        self.preview_image.set_image(clip.get("image"))
        self.lbl_clip_name.setText(f"Cảnh {row + 1} · {clip['id']}")
        image = clip.get("image")
        self.lbl_clip_media.setText(image.name if image else 'Chưa có ảnh')
        self.lbl_clip_media.setToolTip(str(image) if image else "")
        status, valid = self._image_status(image)
        self.lbl_clip_image_status.setText(status)
        self.lbl_clip_image_status.setProperty("valid", valid)
        self.lbl_clip_image_status.style().unpolish(self.lbl_clip_image_status)
        self.lbl_clip_image_status.style().polish(self.lbl_clip_image_status)
        self.txt_clip_image_path.setText(str(image) if image else "")
        self.btn_replace_scene_image.setEnabled(self.project is not None and self.edit_document is not None)
        self.lbl_clip_range.setText(
            f"Thời gian: {video_creator.format_time(clip['start'])} – "
            f"{video_creator.format_time(clip['end'])} ({clip['duration']:.2f}s)"
        )
        motion = clip.get("motion") or {"type": "none"}
        motion_names = {
            "none": "Không", "zoom_in": "Phóng to", "zoom_out": "Thu nhỏ",
            "pan_left": "Di chuyển trái", "pan_right": "Di chuyển phải",
            "pan_up": "Di chuyển lên", "pan_down": "Di chuyển xuống",
            "drift_left": "Trôi trái", "drift_right": "Trôi phải", "shake": "Rung nhẹ",
        }
        self.lbl_clip_motion.setText(f"Chuyển động: {motion_names.get(motion.get('type'), 'Không')}")
        subtitle_ids = clip.get("subtitles", [])
        if self.edit_document:
            subtitles = {entry["id"]: entry["text"] for entry in
                         self.edit_document["tracks"]["subtitles"]}
            content = "\n".join(subtitles.get(sub_id, "") for sub_id in subtitle_ids).strip()
        else:
            content = ", ".join(map(str, subtitle_ids))
        self.lbl_clip_subtitles.setText(content or '—')
        for index, button in enumerate(self._scene_buttons):
            button.setProperty("selected", index == row)
            button.style().unpolish(button)
            button.style().polish(button)

    def choose_scene_image(self):
        row = self._selected_scene
        if row is None or self.edit_document is None or not self.project:
            return
        if self.worker and self.worker.isRunning():
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        current = self.current_timeline[row].get("image")
        source_value = self.txt_image_dir.text().strip().strip('"')
        source_dir = Path(source_value) if source_value else self.project.path
        initial = current.parent if current and current.parent.is_dir() else (
            source_dir if source_dir.is_dir() else self.project.path
        )
        selected, _ = QFileDialog.getOpenFileName(
            self, f"Thay ảnh cho cảnh {self.current_timeline[row]['id']}", str(initial),
            "Ảnh (*.png *.jpg *.jpeg *.webp *.bmp);;Tất cả tệp (*.*)",
        )
        if selected:
            self._replace_scene_image(Path(selected), row)

    def _replace_scene_image(self, image_path: Path, row: Optional[int] = None) -> bool:
        if row is None:
            row = self._selected_scene
        if (self.edit_document is None or not self.project or row is None
                or not 0 <= row < len(self.current_timeline)):
            return False
        image_path = Path(image_path).resolve()
        status, valid = self._image_status(image_path)
        if image_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"} or not valid:
            QMessageBox.warning(self, "Ảnh không hợp lệ", f"Không thể dùng tệp này làm ảnh cảnh: {status}.")
            return False
        reference = edit_document.media_reference(self.project.path, image_path)
        clip = self.edit_document["tracks"]["video"][row]
        if clip.get("media") == reference:
            return True
        clip["media"] = reference
        self.current_timeline = edit_document.document_timeline(self.project.path, self.edit_document)
        self._edit_dirty = True
        self.panel_result.setVisible(False)
        self._show_timeline(self.current_timeline)
        if self.auto_save:
            if self.save_current_state():
                self.lbl_status.setText(f"Đã thay và tự động lưu ảnh cho cảnh {clip['scene_id']}.")
            else:
                self.lbl_status.setText("Ảnh đã thay trong bản dựng nhưng chưa lưu được. Hãy thử Lưu lại.")
        else:
            self.lbl_status.setText(f"Đã thay ảnh cho cảnh {clip['scene_id']}. Nhấn Lưu để giữ thay đổi.")
        return True

    def _configure_preview_audio(self):
        if self.edit_document and self.project:
            reference = self.edit_document["tracks"]["audio"][0]["media"]
            path = edit_document.media_path(self.project.path, reference)
        else:
            value = self.txt_audio_file.text().strip().strip('"')
            path = Path(value) if value else None
        path = path.resolve() if path and path.is_file() else None
        changed = path != self._preview_audio_path
        if changed:
            self.player.stop()
            self._preview_audio_path = path
            self.player.setSource(QUrl.fromLocalFile(str(path)) if path else QUrl())
        self.btn_play_pause.setEnabled(path is not None and bool(self.current_timeline))
        self.btn_play_pause.setToolTip(str(path) if path else "Không tìm thấy file voice của bản dựng")
        return changed

    def seek_preview(self, position_ms: int):
        limit = round(self.total_audio_duration * 1000)
        position_ms = max(0, min(int(position_ms), limit))
        self._update_playhead(position_ms)
        if self._preview_audio_path:
            self.player.setPosition(position_ms)

    def _on_player_position_changed(self, position_ms: int):
        self._update_playhead(position_ms)

    def _update_playhead(self, position_ms: int):
        limit = round(self.total_audio_duration * 1000)
        self._playhead_ms = max(0, min(position_ms, limit))
        with QSignalBlocker(self.slider_playhead):
            self.slider_playhead.setValue(self._playhead_ms)
        position = self._playhead_ms / 1000
        self.time_ruler.set_position(position)
        if self.current_timeline:
            scrollbar = self.timeline_scroll.horizontalScrollBar()
            marker_x = 8 + self.time_ruler.TRACK_OFFSET + round(
                position * self.time_ruler.PIXELS_PER_SECOND
            )
            viewport_width = self.timeline_scroll.viewport().width()
            if marker_x < scrollbar.value() or marker_x > scrollbar.value() + viewport_width - 20:
                scrollbar.setValue(marker_x - viewport_width // 2)
        self.lbl_preview_time.setText(
            f"{video_creator.format_time(position)} / "
            f"{video_creator.format_time(self.total_audio_duration)}"
        )
        row = next((index for index, clip in enumerate(self.current_timeline)
                    if clip["start"] <= position < clip["end"]), None)
        if row is None and self.current_timeline and self._playhead_ms == limit:
            row = len(self.current_timeline) - 1
        if row is not None and row != self._selected_scene:
            self._select_scene(row, seek=False)
        elif row is None:
            self._selected_scene = None
            self.table.clearSelection()
            self.preview_image.show_gap()
            self.lbl_clip_name.setText("Chưa có cảnh tại mốc này")
            self.lbl_clip_media.setText("Ảnh: —")
            self.lbl_clip_image_status.setText("Trạng thái ảnh: —")
            self.txt_clip_image_path.clear()
            self.lbl_clip_range.setText("Thời gian: —")
            self.lbl_clip_motion.setText("Chuyển động: —")
            self.lbl_clip_subtitles.setText("Phụ đề: —")
            self.btn_replace_scene_image.setEnabled(False)
            for button in self._scene_buttons:
                button.setProperty("selected", False)
                button.style().unpolish(button)
                button.style().polish(button)
        subtitle = "\n".join(
            entry["text"] for entry in self._preview_subtitles
            if entry["start"] <= position < entry["end"] and entry["text"]
        )
        self.preview_image.set_subtitle(subtitle if self.chk_subtitles.isChecked() else "")

    def toggle_preview_playback(self):
        if not self._preview_audio_path:
            return
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self._playhead_ms >= round(self.total_audio_duration * 1000):
                self.seek_preview(0)
            self.player.play()

    def _on_playback_state_changed(self, state):
        self.btn_play_pause.setText(
            "⏸ Tạm dừng" if state == QMediaPlayer.PlaybackState.PlayingState else "▶ Phát voice"
        )

    def _on_preview_error(self, error, message):
        if error != QMediaPlayer.Error.NoError:
            self.lbl_status.setText(f"Không thể phát voice: {message}")
            self.btn_play_pause.setText("▶ Phát voice")

    def hideEvent(self, event):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.player.stop()
        self.player.setSource(QUrl())
        super().closeEvent(event)

    # ================= TỰ ĐỘNG PHÁT HIỆN & BROWSE =================
    def auto_detect_defaults(self):
        """Tự động tìm kiếm các asset mới nhất — ưu tiên từ dự án hiện tại."""
        if self.edit_document is not None:
            return
        if self.project and self.project.edit_path.exists():
            self._load_saved_edit()
            return
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

        # ========== 1. Tìm ảnh ==========
        found_img_dir = None

        # Ưu tiên thư mục ảnh của project
        if self.project:
            eff = self.project.get_effective_image_dir()
            if eff.exists() and any(f.suffix.lower() in valid_exts for f in eff.iterdir() if f.is_file()):
                found_img_dir = eff

        # Fallback: quét các thư mục phổ biến
        if not found_img_dir:
            base_dir = config.APP_DIR
            parent_dir = base_dir.parent
            candidate_img_dirs = [
                config.DOWNLOADS_DIR / "images" / "clean",
                config.DOWNLOADS_DIR / "images",
                config.DOWNLOADS_DIR,
                base_dir / "images" / "clean",
                base_dir / "images",
            ]
            for p in candidate_img_dirs:
                if p.exists() and p.is_dir():
                    try:
                        if any(f.suffix.lower() in valid_exts for f in p.iterdir() if f.is_file()):
                            found_img_dir = p
                            break
                    except Exception:
                        pass

        if found_img_dir:
            self.txt_image_dir.setText(str(found_img_dir.resolve()))
        else:
            self.txt_image_dir.setText("")

        # ========== 2. Tìm audio (voice mp3/wav) ==========
        found_audio = None

        # Ưu tiên file voice mới nhất từ project
        if self.project:
            voice = self.project.get_latest_voice()
            if voice:
                found_audio = voice

        # Fallback: quét downloads
        if not found_audio:
            candidate_audios = list(config.DOWNLOADS_DIR.glob("*.mp3")) + list(config.DOWNLOADS_DIR.glob("*.wav"))
            if candidate_audios:
                candidate_audios.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                found_audio = candidate_audios[0]

        if found_audio:
            self.txt_audio_file.setText(str(found_audio.resolve()))
        else:
            self.txt_audio_file.setText("")

        # ========== 3. Tìm SRT ==========
        found_srt = None

        # Nếu đã có audio_file, ưu tiên tìm file .srt cùng tên
        curr_audio = self.txt_audio_file.text().strip().strip('"')
        if curr_audio and Path(curr_audio).exists():
            cand_same = Path(curr_audio).with_suffix(".srt")
            if cand_same.exists():
                found_srt = cand_same

        # Ưu tiên file SRT mới nhất từ project
        if not found_srt and self.project:
            srt = self.project.get_latest_srt()
            if srt:
                found_srt = srt

        # Fallback: quét downloads
        if not found_srt:
            candidate_srts = list(config.DOWNLOADS_DIR.glob("*.srt"))
            if candidate_srts:
                candidate_srts.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                found_srt = candidate_srts[0]

        if found_srt:
            self.txt_srt_file.setText(str(found_srt.resolve()))
        else:
            self.txt_srt_file.setText("")

        self.generate_default_output_name()

    def set_project(self, project):
        """Đồng bộ hóa toàn bộ tài nguyên đầu vào theo Dự Án được chọn."""
        self.player.stop()
        self.player.setSource(QUrl())
        self._preview_audio_path = None
        self._preview_subtitles = []
        self._playhead_ms = 0
        self.edit_document = None
        self._edit_dirty = False
        self.btn_preview.setText("Tạo timeline")
        with QSignalBlocker(self.chk_subtitles):
            self.chk_subtitles.setChecked(False)
        self._selected_scene = None
        self.current_timeline = []
        self.total_audio_duration = 0.0
        self.last_output_video = None
        self.table.setRowCount(0)
        self.lbl_summary_scenes.setText("0 cảnh")
        self.lbl_summary_duration.setText("00:00.000")
        self.lbl_summary_images.setText("Chưa phân tích")
        self.panel_result.setVisible(False)
        self.preview_image.set_image(None)
        self.preview_image.set_subtitle("")
        self.slider_playhead.setRange(0, 0)
        self.btn_play_pause.setEnabled(False)
        self.time_ruler.set_duration(0)
        self.time_ruler.set_position(0)
        self.lbl_preview_time.setText("00:00.000 / 00:00.000  ·  Chưa chọn cảnh")
        self.lbl_clip_name.setText("Chưa chọn cảnh")
        self.lbl_clip_media.setText("Ảnh: —")
        self.lbl_clip_image_status.setText("Trạng thái ảnh: —")
        self.txt_clip_image_path.clear()
        self.btn_replace_scene_image.setEnabled(False)
        self.lbl_clip_range.setText("Thời gian: —")
        self.lbl_clip_motion.setText("Chuyển động: —")
        self.lbl_clip_subtitles.setText("Phụ đề: —")
        self.project = project
        self.btn_rebuild.setVisible(project is not None)
        self._json_data = None
        if not project:
            if hasattr(self, "lbl_project_badge"):
                self.lbl_project_badge.setText("📁 Chưa chọn dự án")
                self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
                self.txt_image_dir.clear()
                self.txt_audio_file.clear()
                self.txt_srt_file.clear()
                self.txt_json_file.clear()
                self.txt_output_path.clear()
                self.table.setRowCount(0)
                self.panel_result.setVisible(False)
            self._refresh_asset_library()
            self._refresh_timeline_tracks()
            return

        if hasattr(self, "lbl_project_badge"):
            self.lbl_project_badge.setVisible(False)

        # 1. Thư mục ảnh sạch
        eff_img_dir = project.get_effective_image_dir()
        self.txt_image_dir.setText(str(eff_img_dir.resolve()))

        # 2. File âm thanh (voice)
        voice = project.get_latest_voice()
        if voice:
            self.txt_audio_file.setText(str(voice.resolve()))
        else:
            self.txt_audio_file.setText("")

        # 3. File SRT
        srt = project.get_latest_srt()
        if not srt and voice:
            cand_srt = voice.with_suffix(".srt")
            if cand_srt.exists():
                srt = cand_srt
        if srt:
            self.txt_srt_file.setText(str(srt.resolve()))
        else:
            self.txt_srt_file.setText("")

        # Kịch bản JSON chỉ được nhận sau khi nhập ở bước 3.
        self.txt_json_file.setText("")

        # 5. Tỉ lệ khung hình
        for idx in range(self.combo_ratio.count()):
            if self.combo_ratio.itemData(idx) == project.aspect_ratio:
                self.combo_ratio.setCurrentIndex(idx)
                break

        # 6. FPS
        for idx in range(self.combo_fps.count()):
            if self.combo_fps.itemData(idx) == project.fps:
                self.combo_fps.setCurrentIndex(idx)
                break

        # 7. Output video path
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_p = project.output_dir / f"video_{ts}.mp4"
        self.txt_output_path.setText(str(out_p.resolve()))

        # Tự động phân tích nếu các file đều hợp lệ
        if project.edit_path.exists():
            self._load_saved_edit()
        elif eff_img_dir.exists() and voice and srt and self.txt_json_file.text():
            self.analyze_timeline()
        else:
            self.lbl_status.setText(f"Đã chuyển sang dự án '{project.name}'.")
        self._refresh_asset_library()
        if not self.current_timeline:
            self._refresh_timeline_tracks()

    def generate_default_output_name(self):
        """Tạo tên mặc định cho video xuất ra theo timestamp."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.project:
            out_p = self.project.output_dir / f"video_{ts}.mp4"
        else:
            out_p = config.DOWNLOADS_DIR / f"video_{ts}.mp4"
        self.txt_output_path.setText(str(out_p.resolve()))

    def on_input_changed(self):
        self.panel_result.setVisible(False)
        self._refresh_asset_library()
        if self._loading_edit:
            return
        if self.edit_document is not None:
            self.lbl_status.setText("Đã đổi nguồn. Bản dựng hiện tại được giữ; chọn 'Tạo lại timeline từ nguồn' để áp dụng.")
        else:
            self.current_timeline = []
            self.total_audio_duration = 0.0
            self.table.setRowCount(0)
            self._preview_subtitles = []
            self.player.stop()
            self.btn_play_pause.setEnabled(False)
            self.preview_image.set_subtitle("")
            self.btn_replace_scene_image.setEnabled(False)
            self.slider_playhead.setRange(0, 0)
            self._playhead_ms = 0
            self._refresh_timeline_tracks()
            self._update_playhead(0)

    def set_audio_and_srt(self, audio_path: str, srt_path: str):
        """Được gọi từ MainWindow hoặc TTSTab khi vừa tạo xong voice & srt."""
        if audio_path and Path(audio_path).exists():
            p_audio = Path(audio_path).resolve()
            self.txt_audio_file.setText(str(p_audio))
            # Nếu srt_path chưa có hoặc không tồn tại, tự tìm file .srt cùng tên
            if not srt_path or not Path(srt_path).exists():
                candidate = p_audio.with_suffix(".srt")
                if candidate.exists():
                    srt_path = str(candidate.resolve())
                elif self.project:
                    proj_srt = self.project.get_latest_srt()
                    if proj_srt and proj_srt.exists():
                        srt_path = str(proj_srt.resolve())

        if srt_path and Path(srt_path).exists():
            self.txt_srt_file.setText(str(Path(srt_path).resolve()))
        self.generate_default_output_name()
        self.lbl_status.setText("Đã nạp file Voice & SRT vừa tạo từ tab TTS.")
        self.analyze_timeline()

    def set_json_file(self, json_source):
        """Nhận nội dung JSON hoặc đường dẫn file kịch bản từ bước 3."""
        self._json_data = None if isinstance(json_source, str) else json_source
        self.txt_json_file.setText(json_source if isinstance(json_source, str) else "")
        self.on_input_changed()

    def set_auto_save(self, enabled: bool):
        self.auto_save = enabled

    def _on_export_settings_changed(self):
        self.preview_image.set_aspect_ratio(self.combo_ratio.currentData() or "16:9")
        if not self._loading_edit and self.current_timeline:
            self._update_playhead(self._playhead_ms)
        if self._loading_edit or self.edit_document is None:
            return
        self.edit_document["settings"].update({
            "aspect_ratio": self.combo_ratio.currentData(),
            "fps": self.combo_fps.currentData(),
            "subtitles_enabled": self.chk_subtitles.isChecked(),
        })
        self._edit_dirty = True
        if self.auto_save:
            self.save_current_state()

    def save_current_state(self) -> bool:
        if not self.project or self.edit_document is None or not self._edit_dirty:
            return True
        try:
            self.project.save_edit_document(self.edit_document, overwrite=True)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Không thể lưu bản dựng", str(exc))
            return False
        self._edit_dirty = False
        return True

    def _apply_edit_document(self, document):
        self.btn_preview.setText("Kiểm tra timeline")
        timeline = edit_document.document_timeline(self.project.path, document)
        self._loading_edit = True
        try:
            sources = document["sources"]
            self.txt_image_dir.setText(str(edit_document.media_path(self.project.path, sources["image_dir"])))
            voice = document["tracks"]["audio"][0]
            self.txt_audio_file.setText(str(edit_document.media_path(self.project.path, voice["media"])))
            self.txt_srt_file.setText(str(edit_document.media_path(self.project.path, sources["srt"])))
            self.combo_ratio.setCurrentIndex(self.combo_ratio.findData(document["settings"]["aspect_ratio"]))
            self.combo_fps.setCurrentIndex(self.combo_fps.findData(document["settings"]["fps"]))
            self.chk_subtitles.setChecked(document["settings"].get("subtitles_enabled", False))
            self.edit_document = document
            self.current_timeline = timeline
            self._preview_subtitles = document["tracks"]["subtitles"]
            self.total_audio_duration = document["duration"]
            self._edit_dirty = False
        finally:
            self._loading_edit = False
        self._show_timeline(timeline)

    def _load_saved_edit(self) -> bool:
        try:
            document = self.project.load_edit_document()
            if document is None:
                return False
            self._apply_edit_document(document)
        except (OSError, ValueError) as exc:
            self.lbl_status.setText(f"Không thể mở bản dựng: {exc} File đã lưu được giữ nguyên.")
            return False
        self.lbl_status.setText("Đã mở bản dựng. Chọn 'Tạo lại từ nguồn' trong thư viện để nhập lại dữ liệu.")
        return True

    def rebuild_timeline(self):
        if self.worker and self.worker.isRunning():
            return
        if self.project and (self.edit_document is not None or self.project.edit_path.exists()):
            answer = QMessageBox.question(
                self, "Tạo lại bản dựng",
                "Tạo lại timeline sẽ thay các chỉnh sửa bằng ảnh, voice, SRT và kịch bản đang chọn.\n"
                "Bản đã lưu trước đó sẽ được sao lưu vào edit.json.bak. Tiếp tục?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._build_timeline_from_sources(replace_existing=True)

    def browse_image_dir(self):
        init_dir = self.txt_image_dir.text().strip() or str(config.DOWNLOADS_DIR)
        path = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa ảnh cảnh (Mặc định: downloads)", init_dir)
        if path:
            self.txt_image_dir.setText(path)
            self.analyze_timeline()

    def browse_audio_file(self):
        init_dir = str(config.DOWNLOADS_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file âm thanh (Mặc định: downloads)", init_dir, "Audio Files (*.mp3 *.wav *.m4a *.aac *.ogg);;All Files (*.*)"
        )
        if path:
            self.txt_audio_file.setText(path)
            self.analyze_timeline()

    def browse_srt_file(self):
        init_dir = str(config.DOWNLOADS_DIR)
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file phụ đề SRT (Mặc định: downloads)", init_dir, "SRT Files (*.srt);;All Files (*.*)"
        )
        if path:
            self.txt_srt_file.setText(path)
            self.analyze_timeline()

    def browse_output_file(self):
        init_path = self.txt_output_path.text().strip() or str(config.DOWNLOADS_DIR / "output_video.mp4")
        path, _ = QFileDialog.getSaveFileName(
            self, "Chọn đường dẫn lưu video", init_path, "MP4 Video (*.mp4);;All Files (*.*)"
        )
        if path:
            if not path.lower().endswith(".mp4"):
                path += ".mp4"
            self.txt_output_path.setText(path)

    # ================= DRAG & DROP =================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            p = Path(url.toLocalFile())
            if p.is_dir():
                self.txt_image_dir.setText(str(p.resolve()))
            elif p.is_file():
                suf = p.suffix.lower()
                if suf in [".mp3", ".wav", ".m4a", ".aac", ".ogg"]:
                    self.txt_audio_file.setText(str(p.resolve()))
                elif suf == ".srt":
                    self.txt_srt_file.setText(str(p.resolve()))
        event.acceptProposedAction()
        self.analyze_timeline()

    # ================= PHÂN TÍCH TIMELINE =================
    def analyze_timeline(self) -> bool:
        """Phân tích các tệp đầu vào và nạp dữ liệu vào bảng Timeline."""
        if self.edit_document is not None:
            self.current_timeline = edit_document.document_timeline(self.project.path, self.edit_document)
            self._show_timeline(self.current_timeline)
            self.lbl_status.setText("Đang dùng bản dựng hiện tại. Chọn 'Tạo lại timeline từ nguồn' để áp dụng nguồn mới.")
            return True
        if self.project and self.project.edit_path.exists():
            return self._load_saved_edit()
        return self._build_timeline_from_sources()

    def _build_timeline_from_sources(self, *, replace_existing=False) -> bool:
        img_dir_str = self.txt_image_dir.text().strip().strip('"')
        aud_file_str = self.txt_audio_file.text().strip().strip('"')
        srt_file_str = self.txt_srt_file.text().strip().strip('"')
        json_file_str = self.txt_json_file.text().strip().strip('"')

        if not img_dir_str or not Path(img_dir_str).is_dir():
            self.lbl_status.setText("Chưa chọn hoặc thư mục ảnh không hợp lệ.")
            return False
        if not aud_file_str or not Path(aud_file_str).is_file():
            self.lbl_status.setText("Chưa chọn hoặc file âm thanh không hợp lệ.")
            return False
        if not srt_file_str or not Path(srt_file_str).is_file():
            self.lbl_status.setText("Chưa chọn hoặc file SRT không hợp lệ.")
            return False
        if self._json_data is None and (not json_file_str or not Path(json_file_str).is_file()):
            self.lbl_status.setText("Chưa chọn hoặc file JSON kịch bản không hợp lệ.")
            return False

        image_dir = Path(img_dir_str)
        audio_path = Path(aud_file_str)
        srt_path = Path(srt_file_str)

        try:
            ffmpeg_exe = video_creator.get_ffmpeg_path()
        except Exception as e:
            QMessageBox.critical(self, "Thiếu FFmpeg", f"Không tìm thấy FFmpeg: {e}")
            return False

        try:
            self.lbl_status.setText("Đang đọc phụ đề và đo thời lượng âm thanh...")
            subtitles = video_creator.parse_srt_file(srt_path)
            total_duration = video_creator.get_audio_duration(ffmpeg_exe, audio_path)
            if self._json_data is not None:
                scenes = video_creator.parse_json_data(self._json_data, sorted(subtitles))
            else:
                scenes = video_creator.parse_json_mapping(Path(json_file_str), sorted(subtitles))
            timeline = video_creator.compute_timeline(scenes, subtitles, total_duration, image_dir)
            if self.project:
                document = edit_document.create_document(
                    self.project.path, timeline, subtitles, image_dir, audio_path, srt_path,
                    self.combo_ratio.currentData(), self.combo_fps.currentData(), total_duration,
                    subtitles_enabled=self.chk_subtitles.isChecked(),
                )
                self.project.save_edit_document(document, overwrite=replace_existing, backup=replace_existing)
                self._apply_edit_document(document)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi phân tích", f"Không thể phân tích dữ liệu: {e}")
            self.lbl_status.setText(f"Lỗi: {e}")
            return False

        if not self.project:
            self.current_timeline = timeline
            self._preview_subtitles = list(subtitles.values())
            self.total_audio_duration = total_duration
            self._show_timeline(timeline)
        else:
            self.lbl_status.setText("Đã tạo và lưu bản dựng.")
        return True

    def _show_timeline(self, timeline):
        self.populate_table(timeline)
        self._refresh_asset_library()
        self._refresh_timeline_tracks()
        audio_changed = self._configure_preview_audio()
        self.slider_playhead.setRange(0, max(0, round(self.total_audio_duration * 1000)))
        self._selected_scene = None
        self._update_playhead(0 if audio_changed else self._playhead_ms)

        # Cập nhật thông số tóm tắt
        problem_count = sum(1 for item in timeline if not self._image_status(item["image"])[1])
        total_scenes = len(timeline)

        self.lbl_summary_scenes.setText(f"{total_scenes} cảnh")
        self.lbl_summary_duration.setText(f"{video_creator.format_time(self.total_audio_duration)} ({self.total_audio_duration:.2f}s)")

        if problem_count == 0:
            self.lbl_summary_images.setText(f"Đủ {total_scenes}/{total_scenes} ảnh")
            self.lbl_summary_images.setStyleSheet("color: #9eafc8; font-size: 11px;")
            self.lbl_status.setText(f"Phân tích hoàn tất: {total_scenes} cảnh, đã tìm thấy đầy đủ ảnh tương ứng.")
        else:
            self.lbl_summary_images.setText(f"⚠ Cần sửa {problem_count}/{total_scenes} ảnh")
            self.lbl_summary_images.setStyleSheet("color: #f0a2a2; font-size: 11px;")
            self.lbl_status.setText(f"Cảnh báo: Có {problem_count} cảnh thiếu ảnh hoặc ảnh không đọc được.")

    def populate_table(self, timeline: List[Dict[str, Any]]):
        """Nạp dữ liệu mốc thời gian vào QTableWidget."""
        self.table.setRowCount(len(timeline))
        for row, item in enumerate(timeline):
            # STT
            stt_item = QTableWidgetItem(str(item["index"]))
            stt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, stt_item)

            # Scene ID
            id_item = QTableWidgetItem(item["id"])
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            id_item.setForeground(QColor("#dce7fa"))
            self.table.setItem(row, 1, id_item)

            # Phụ đề
            subs_str = ", ".join(map(str, item["subtitles"])) if item["subtitles"] else "(Tự động)"
            sub_item = QTableWidgetItem(subs_str)
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sub_item.setForeground(QColor("#9ca6b7"))
            self.table.setItem(row, 2, sub_item)

            # File ảnh
            img_p = item["image"]
            status, valid = self._image_status(img_p)
            if valid:
                img_item = QTableWidgetItem(f"✓ {img_p.name}")
                img_item.setForeground(QColor("#cbd2de"))
            else:
                img_item = QTableWidgetItem(f"✗ {img_p.name}" if img_p else "✗ CHƯA CÓ ẢNH")
                img_item.setForeground(QColor("#f87171"))
            img_item.setToolTip(f"{status}\n{img_p if img_p else ''}")
            self.table.setItem(row, 3, img_item)

            # Bắt đầu
            start_item = QTableWidgetItem(video_creator.format_time(item["start"]))
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            start_item.setForeground(QColor("#aeb8c8"))
            self.table.setItem(row, 4, start_item)

            # Kết thúc
            end_item = QTableWidgetItem(video_creator.format_time(item["end"]))
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            end_item.setForeground(QColor("#aeb8c8"))
            self.table.setItem(row, 5, end_item)

            # Thời lượng
            dur_item = QTableWidgetItem(f"{item['duration']:.2f}s")
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            dur_item.setForeground(QColor("#aeb8c8"))
            self.table.setItem(row, 6, dur_item)

    def on_table_row_clicked(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self.current_timeline):
            self._select_scene(row)
            sc = self.current_timeline[row]
            img = sc.get("image")
            if img and img.exists():
                self.lbl_status.setText(f"Cảnh {sc['id']}: {img.name} (Bắt đầu: {video_creator.format_time(sc['start'])}, Thời lượng: {sc['duration']:.2f}s)")

    # ================= TIẾN HÀNH GHÉP VIDEO =================
    def start_render(self):
        """Bắt đầu ghép video bằng FFmpeg."""
        if self.worker and self.worker.isRunning():
            return
        if not self.current_timeline:
            if not self.analyze_timeline():
                return

        saved_document = None
        if self.edit_document is not None:
            if not self.save_current_state():
                return
            try:
                saved_document = self.project.load_edit_document()
            except (OSError, ValueError) as exc:
                QMessageBox.warning(self, "Không thể đọc bản dựng", str(exc))
                return

        aspect_ratio = self.combo_ratio.currentData() or "16:9"
        fps = int(self.combo_fps.currentData() or 30)
        subtitles_enabled = self.chk_subtitles.isChecked()
        if saved_document is not None:
            aspect_ratio = saved_document["settings"]["aspect_ratio"]
            fps = saved_document["settings"]["fps"]
            subtitles_enabled = saved_document["settings"].get("subtitles_enabled", False)
        render_timeline = (edit_document.render_timeline(self.project.path, saved_document, fps)
                           if saved_document is not None else deepcopy(self.current_timeline))
        for clip in render_timeline:
            if clip["image"] is not None and not clip["image"].is_file():
                clip["image"] = None
        missing = [it for it in render_timeline if it["image"] is None and it["id"] != "gap"]
        if missing:
            reply = QMessageBox.question(
                self,
                "Thiếu ảnh cho cảnh",
                f"Có {len(missing)} cảnh không tìm thấy ảnh.\nBạn có muốn tiếp tục xuất, dùng khung đen cho các cảnh này không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        out_str = self.txt_output_path.text().strip().strip('"')
        if not out_str:
            self.generate_default_output_name()
            out_str = self.txt_output_path.text().strip()
        output_path = Path(out_str)

        audio_path = Path(self.txt_audio_file.text().strip().strip('"'))
        if saved_document is not None:
            audio_path = edit_document.media_path(self.project.path, saved_document["tracks"]["audio"][0]["media"])
        if not audio_path.is_file():
            QMessageBox.warning(self, "Thiếu voice", f"Không tìm thấy file voice của bản dựng: {audio_path}")
            return
        if saved_document is not None:
            render_subtitles = deepcopy(saved_document["tracks"]["subtitles"]) if subtitles_enabled else []
        else:
            render_subtitles = deepcopy(self._preview_subtitles) if subtitles_enabled else None
        self.btn_start.setEnabled(False)
        self.btn_start.setVisible(False)
        self.btn_preview.setEnabled(False)
        self.btn_rebuild.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)
        self.panel_result.setVisible(False)
        self.progress_bar.setValue(5)
        self.progress_bar.show()
        self.lbl_status.setText("Đang khởi tạo FFmpeg...")

        self.worker = VideoRenderWorker(
            timeline=render_timeline,
            audio_path=audio_path,
            output_path=output_path,
            total_audio_duration=(saved_document["duration"] if saved_document else self.total_audio_duration),
            aspect_ratio=aspect_ratio,
            fps=fps,
            subtitles=render_subtitles,
        )
        self.worker.progress_updated.connect(self.on_render_progress)
        self.worker.render_finished.connect(self.on_render_finished)
        self.worker.start()

    def cancel_render(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.lbl_status.setText("Đang hủy tác vụ ghép video...")
            self.btn_cancel.setEnabled(False)

    def on_render_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def on_render_finished(self, success: bool, res: dict):
        self.progress_bar.hide()
        self.btn_start.setEnabled(True)
        self.btn_start.setVisible(True)
        self.btn_preview.setEnabled(True)
        self.btn_rebuild.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Đã xuất video.")
            if self.project:
                self.project.save_metadata()
            out_p = res.get("output_path")
            self.last_output_video = out_p
            if out_p:
                self.video_rendered.emit(str(out_p))
            dur = res.get("duration", 0.0)
            size_mb = res.get("size_mb", 0.0)
            details = f"{Path(out_p).name if out_p else 'Video đã xuất'} · {size_mb:.1f} MB · {video_creator.format_time(dur)}"
            self.lbl_res_details.setText(details)
            self.lbl_res_details.setToolTip(str(out_p or ""))
            self.panel_result.setVisible(True)
        else:
            err = res.get("error", "Lỗi không xác định")
            self.lbl_status.setText(f"Ghép video thất bại: {err}")
            QMessageBox.critical(self, "Ghép Video Thất Bại", f"Không thể xuất video:\n\n{err}")

    # ================= MỞ FILE & THƯ MỤC =================
    def open_video_file(self):
        if self.last_output_video and self.last_output_video.exists():
            try:
                open_path(self.last_output_video)
            except Exception as e:
                QMessageBox.warning(self, "Không thể mở", f"Lỗi mở video: {e}")

    def open_output_dir(self):
        out_dir = self.project.output_dir if self.project and self.project.output_dir.exists() else config.DOWNLOADS_DIR
        if self.last_output_video and self.last_output_video.parent.exists():
            out_dir = self.last_output_video.parent

        try:
            open_path(out_dir)
        except Exception as e:
            QMessageBox.warning(self, "Không thể mở", f"Lỗi mở thư mục: {e}")

    def copy_output_path(self):
        if self.last_output_video:
            clipboard = QApplication.clipboard()
            clipboard.setText(str(self.last_output_video))
            self.lbl_status.setText("Đã sao chép đường dẫn video vào bộ nhớ tạm (Clipboard).")

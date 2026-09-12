import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QProgressBar, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QSplitter, QScrollArea, QApplication, QSizePolicy
)

from app import config
from app.core import video_creator


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
        fps: int = 30
    ):
        super().__init__()
        self.timeline = timeline
        self.audio_path = audio_path
        self.output_path = output_path
        self.total_audio_duration = total_audio_duration
        self.aspect_ratio = aspect_ratio
        self.fps = fps
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        def on_prog(pct: int, msg: str):
            self.progress_updated.emit(pct, msg)

        res = video_creator.render_video(
            timeline=self.timeline,
            audio_path=self.audio_path,
            output_path=self.output_path,
            total_audio_duration=self.total_audio_duration,
            aspect_ratio=self.aspect_ratio,
            fps=self.fps,
            progress_callback=on_prog,
            is_cancelled=lambda: self._is_cancelled
        )
        self.render_finished.emit(res.get("success", False), res)


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

        self.init_ui()
        self.auto_detect_defaults()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(10)

        # Splitter chia 2 cột: Cột trái (Cấu hình đầu vào), Cột phải (Bảng Timeline & Kết quả)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("video_splitter")

        # ================= CỘT TRÁI: ĐẦU VÀO & THIẾT LẬP =================
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        left_scroll.setMinimumWidth(430)
        left_scroll.setMaximumWidth(620)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 10, 4)
        left_layout.setSpacing(12)

        # Card 1: Nạp Tệp Đầu Vào
        panel_inputs = QFrame()
        panel_inputs.setProperty("class", "panel")
        in_layout = QVBoxLayout(panel_inputs)
        in_layout.setContentsMargins(14, 14, 14, 14)
        in_layout.setSpacing(10)

        header_row = QHBoxLayout()
        lbl_in_title = QLabel("1. Tệp Đầu Vào (Assets)")
        lbl_in_title.setProperty("class", "panel_title")
        header_row.addWidget(lbl_in_title)
        header_row.addStretch()

        self.lbl_project_badge = QLabel("📁 Chưa chọn dự án")
        self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
        header_row.addWidget(self.lbl_project_badge)
        in_layout.addLayout(header_row)

        # 1. Thư mục ảnh
        lbl_img = QLabel("Thư mục chứa ảnh:")
        lbl_img.setProperty("class", "section_label")
        in_layout.addWidget(lbl_img)
        box_img = QHBoxLayout()
        box_img.setSpacing(6)
        self.txt_image_dir = QLineEdit()
        self.txt_image_dir.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.txt_image_dir.setPlaceholderText("Đường dẫn thư mục ảnh (Mặc định: downloads)...")
        self.txt_image_dir.textChanged.connect(self.on_input_changed)
        btn_browse_img = QPushButton("Chọn...")
        btn_browse_img.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        btn_browse_img.clicked.connect(self.browse_image_dir)
        box_img.addWidget(self.txt_image_dir)
        box_img.addWidget(btn_browse_img)
        in_layout.addLayout(box_img)

        # 2. File âm thanh
        lbl_aud = QLabel("File âm thanh voice (.mp3, .wav...):")
        lbl_aud.setProperty("class", "section_label")
        in_layout.addWidget(lbl_aud)
        box_aud = QHBoxLayout()
        box_aud.setSpacing(6)
        self.txt_audio_file = QLineEdit()
        self.txt_audio_file.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.txt_audio_file.setPlaceholderText("Đường dẫn file voice .mp3 (Mặc định: downloads)...")
        self.txt_audio_file.textChanged.connect(self.on_input_changed)
        btn_browse_aud = QPushButton("Chọn...")
        btn_browse_aud.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        btn_browse_aud.clicked.connect(self.browse_audio_file)
        box_aud.addWidget(self.txt_audio_file)
        box_aud.addWidget(btn_browse_aud)
        in_layout.addLayout(box_aud)

        # 3. File phụ đề SRT
        lbl_srt = QLabel("File phụ đề khớp thời gian (.srt):")
        lbl_srt.setProperty("class", "section_label")
        in_layout.addWidget(lbl_srt)
        box_srt = QHBoxLayout()
        box_srt.setSpacing(6)
        self.txt_srt_file = QLineEdit()
        self.txt_srt_file.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.txt_srt_file.setPlaceholderText("Đường dẫn file .srt (Mặc định: downloads)...")
        self.txt_srt_file.textChanged.connect(self.on_input_changed)
        btn_browse_srt = QPushButton("Chọn...")
        btn_browse_srt.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        btn_browse_srt.clicked.connect(self.browse_srt_file)
        box_srt.addWidget(self.txt_srt_file)
        box_srt.addWidget(btn_browse_srt)
        in_layout.addLayout(box_srt)

        # Đường dẫn JSON được quản lý ở bước 3 và chỉ giữ nội bộ tại đây.
        self.txt_json_file = QLineEdit()
        self.txt_json_file.textChanged.connect(self.on_input_changed)

        left_layout.addWidget(panel_inputs)

        # Card 2: Cấu hình Video
        panel_cfg = QFrame()
        panel_cfg.setProperty("class", "panel")
        cfg_layout = QVBoxLayout(panel_cfg)
        cfg_layout.setContentsMargins(14, 14, 14, 14)
        cfg_layout.setSpacing(10)

        lbl_cfg_title = QLabel("2. Cấu Hình Xuất Video")
        lbl_cfg_title.setProperty("class", "panel_title")
        cfg_layout.addWidget(lbl_cfg_title)

        # Tỉ lệ khung hình
        lbl_ratio = QLabel("Tỉ lệ khung hình:")
        lbl_ratio.setProperty("class", "section_label")
        cfg_layout.addWidget(lbl_ratio)
        self.combo_ratio = QComboBox()
        self.combo_ratio.addItem("16:9 (Ngang 1920x1080 - YouTube, Facebook)", "16:9")
        self.combo_ratio.addItem("9:16 (Dọc 1080x1920 - TikTok, Shorts, Reels)", "9:16")
        self.combo_ratio.addItem("1:1 (Vuông 1080x1080 - Instagram, Square)", "1:1")
        cfg_layout.addWidget(self.combo_ratio)

        # FPS
        lbl_fps = QLabel("Tốc độ khung hình (FPS):")
        lbl_fps.setProperty("class", "section_label")
        cfg_layout.addWidget(lbl_fps)
        self.combo_fps = QComboBox()
        self.combo_fps.addItem("30 FPS (Khuyên dùng - Chuẩn & Nhẹ)", 30)
        self.combo_fps.addItem("60 FPS (Mượt mà nhất)", 60)
        self.combo_fps.addItem("24 FPS (Chuẩn Điện ảnh)", 24)
        cfg_layout.addWidget(self.combo_fps)

        # Đường dẫn xuất
        lbl_out = QLabel("Tên & Đường dẫn file video xuất ra:")
        lbl_out.setProperty("class", "section_label")
        cfg_layout.addWidget(lbl_out)
        box_out = QHBoxLayout()
        box_out.setSpacing(6)
        self.txt_output_path = QLineEdit()
        self.txt_output_path.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.txt_output_path.setPlaceholderText("Đường dẫn file .mp4 xuất ra...")
        btn_browse_out = QPushButton("Đổi...")
        btn_browse_out.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        btn_browse_out.clicked.connect(self.browse_output_file)
        box_out.addWidget(self.txt_output_path)
        box_out.addWidget(btn_browse_out)
        cfg_layout.addLayout(box_out)

        left_layout.addWidget(panel_cfg)

        # Card 3: Nút Thao Tác & Tiến Trình
        panel_act = QFrame()
        panel_act.setProperty("class", "panel")
        act_layout = QVBoxLayout(panel_act)
        act_layout.setContentsMargins(14, 14, 14, 14)
        act_layout.setSpacing(10)

        self.btn_preview = QPushButton("🔍  Phân Tích & Xem Trước Timeline")
        self.btn_preview.setObjectName("btn_subtle")
        self.btn_preview.clicked.connect(self.analyze_timeline)
        act_layout.addWidget(self.btn_preview)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_start = QPushButton("🚀  Bắt Đầu Ghép Video")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.setMinimumHeight(38)
        self.btn_start.clicked.connect(self.start_render)
        btn_row.addWidget(self.btn_start, stretch=1)

        self.btn_cancel = QPushButton("⛔  Hủy")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setMinimumHeight(38)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_render)
        btn_row.addWidget(self.btn_cancel, stretch=1)

        act_layout.addLayout(btn_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        act_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet("color: #9ca3af; font-size: 11px;")
        act_layout.addWidget(self.lbl_status)

        left_layout.addWidget(panel_act)
        left_layout.addStretch()

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        # ================= CỘT PHẢI: BẢNG TIMELINE & KẾT QUẢ =================
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 4, 4, 4)
        right_layout.setSpacing(10)

        # Header Bảng Timeline + Badge thống kê
        tb_header_box = QHBoxLayout()
        lbl_tb_title = QLabel("Bảng Phân Bổ Cảnh (Timeline)")
        lbl_tb_title.setProperty("class", "panel_title")
        tb_header_box.addWidget(lbl_tb_title)

        tb_header_box.addStretch()

        self.lbl_summary_scenes = QLabel("0 cảnh")
        self.lbl_summary_scenes.setStyleSheet("background-color: #1e2029; border: 1px solid #2d303b; border-radius: 4px; padding: 3px 8px; font-size: 11px; color: #93c5fd;")
        tb_header_box.addWidget(self.lbl_summary_scenes)

        self.lbl_summary_duration = QLabel("00:00.000")
        self.lbl_summary_duration.setStyleSheet("background-color: #1e2029; border: 1px solid #2d303b; border-radius: 4px; padding: 3px 8px; font-size: 11px; color: #facc15;")
        tb_header_box.addWidget(self.lbl_summary_duration)

        self.lbl_summary_images = QLabel("Chưa phân tích")
        self.lbl_summary_images.setStyleSheet("background-color: #1e2029; border: 1px solid #2d303b; border-radius: 4px; padding: 3px 8px; font-size: 11px; color: #9ca3af;")
        tb_header_box.addWidget(self.lbl_summary_images)

        right_layout.addLayout(tb_header_box)

        # Bảng Table Timeline
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "STT", "Scene ID", "Phụ Đề Gán", "File Ảnh Khớp", "Bắt Đầu", "Kết Thúc", "Thời Lượng"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 48)
        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 95)
        self.table.setColumnWidth(4, 85)
        self.table.setColumnWidth(5, 85)
        self.table.setColumnWidth(6, 85)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.itemClicked.connect(self.on_table_row_clicked)
        right_layout.addWidget(self.table)

        # Card Kết quả Video Xuất Ra
        self.panel_result = QFrame()
        self.panel_result.setProperty("class", "panel")
        self.panel_result.setStyleSheet("background-color: #15221b; border: 1px solid #166534; border-radius: 8px; padding: 12px;")
        self.panel_result.setVisible(False)
        res_layout = QVBoxLayout(self.panel_result)
        res_layout.setContentsMargins(12, 10, 12, 10)
        res_layout.setSpacing(8)

        lbl_res_title = QLabel("🎉 GHÉP VIDEO THÀNH CÔNG!")
        lbl_res_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #4ade80;")
        res_layout.addWidget(lbl_res_title)

        self.lbl_res_details = QLabel("Thông tin video...")
        self.lbl_res_details.setStyleSheet("font-size: 12px; color: #d1fae5; line-height: 140%;")
        res_layout.addWidget(self.lbl_res_details)

        res_btn_box = QHBoxLayout()
        res_btn_box.setSpacing(8)

        self.btn_open_video = QPushButton("▶  Mở Video Ngay")
        self.btn_open_video.setObjectName("btn_primary")
        self.btn_open_video.clicked.connect(self.open_video_file)
        res_btn_box.addWidget(self.btn_open_video)

        self.btn_open_dir = QPushButton("📂  Mở Thư Mục Chứa")
        self.btn_open_dir.clicked.connect(self.open_output_dir)
        res_btn_box.addWidget(self.btn_open_dir)

        self.btn_copy_path = QPushButton("📋  Sao Chép Đường Dẫn")
        self.btn_copy_path.clicked.connect(self.copy_output_path)
        res_btn_box.addWidget(self.btn_copy_path)

        res_btn_box.addStretch()
        res_layout.addLayout(res_btn_box)

        right_layout.addWidget(self.panel_result)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)
        splitter.setSizes([520, 680])

        main_layout.addWidget(splitter)

    # ================= TỰ ĐỘNG PHÁT HIỆN & BROWSE =================
    def auto_detect_defaults(self):
        """Tự động tìm kiếm các asset mới nhất — ưu tiên từ dự án hiện tại."""
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
        previous_slug = getattr(self.project, "slug", None)
        next_slug = getattr(project, "slug", None)
        if previous_slug != next_slug and hasattr(self, "table"):
            self.table.setRowCount(0)
            self.current_timeline = []
            self.last_output_video = None
            self.panel_result.setVisible(False)
        self.project = project
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

        # File JSON chỉ được nhận sau khi khách nhập ở bước 3.
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
        if eff_img_dir.exists() and voice and srt and self.txt_json_file.text():
            self.analyze_timeline()
        else:
            self.lbl_status.setText(f"Đã chuyển sang dự án '{project.name}'.")

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

    def set_json_file(self, json_path: str):
        """Nhận file kịch bản đã chọn ở bước 3."""
        self.txt_json_file.setText(json_path)

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
        if not json_file_str or not Path(json_file_str).is_file():
            self.lbl_status.setText("Chưa chọn hoặc file JSON kịch bản không hợp lệ.")
            return False

        image_dir = Path(img_dir_str)
        audio_path = Path(aud_file_str)
        srt_path = Path(srt_file_str)
        json_path = Path(json_file_str)

        try:
            ffmpeg_exe = video_creator.get_ffmpeg_path()
        except Exception as e:
            QMessageBox.critical(self, "Thiếu FFmpeg", f"Không tìm thấy FFmpeg: {e}")
            return False

        try:
            self.lbl_status.setText("Đang đọc phụ đề và đo thời lượng âm thanh...")
            subtitles = video_creator.parse_srt_file(srt_path)
            self.total_audio_duration = video_creator.get_audio_duration(ffmpeg_exe, audio_path)
            scenes = video_creator.parse_json_mapping(json_path, sorted(list(subtitles.keys())))
            timeline = video_creator.compute_timeline(scenes, subtitles, self.total_audio_duration, image_dir)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi phân tích", f"Không thể phân tích dữ liệu: {e}")
            self.lbl_status.setText(f"Lỗi: {e}")
            return False

        self.current_timeline = timeline
        self.populate_table(timeline)

        # Cập nhật thông số tóm tắt
        missing_count = sum(1 for item in timeline if item["image"] is None)
        total_scenes = len(timeline)

        self.lbl_summary_scenes.setText(f"{total_scenes} cảnh")
        self.lbl_summary_duration.setText(f"{video_creator.format_time(self.total_audio_duration)} ({self.total_audio_duration:.2f}s)")

        if missing_count == 0:
            self.lbl_summary_images.setText(f"✓ Đủ {total_scenes}/{total_scenes} ảnh")
            self.lbl_summary_images.setStyleSheet("background-color: #064e3b; border: 1px solid #065f46; border-radius: 4px; padding: 3px 8px; font-size: 11px; color: #34d399; font-weight: 600;")
            self.lbl_status.setText(f"Phân tích hoàn tất: {total_scenes} cảnh, đã tìm thấy đầy đủ ảnh tương ứng.")
        else:
            self.lbl_summary_images.setText(f"⚠ Thiếu {missing_count}/{total_scenes} ảnh")
            self.lbl_summary_images.setStyleSheet("background-color: #450a0a; border: 1px solid #7f1d1d; border-radius: 4px; padding: 3px 8px; font-size: 11px; color: #f87171; font-weight: 600;")
            self.lbl_status.setText(f"Cảnh báo: Có {missing_count} cảnh chưa tìm thấy ảnh trong thư mục.")

        return True

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
            id_item.setForeground(QColor("#facc15"))
            self.table.setItem(row, 1, id_item)

            # Phụ đề
            subs_str = ", ".join(map(str, item["subtitles"])) if item["subtitles"] else "(Tự động)"
            sub_item = QTableWidgetItem(subs_str)
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            sub_item.setForeground(QColor("#c084fc"))
            self.table.setItem(row, 2, sub_item)

            # File ảnh
            img_p = item["image"]
            if img_p:
                img_item = QTableWidgetItem(f"✓ {img_p.name}")
                img_item.setForeground(QColor("#34d399"))
            else:
                img_item = QTableWidgetItem("✗ CHƯA CÓ ẢNH")
                img_item.setForeground(QColor("#f87171"))
            self.table.setItem(row, 3, img_item)

            # Bắt đầu
            start_item = QTableWidgetItem(video_creator.format_time(item["start"]))
            start_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            start_item.setForeground(QColor("#4ade80"))
            self.table.setItem(row, 4, start_item)

            # Kết thúc
            end_item = QTableWidgetItem(video_creator.format_time(item["end"]))
            end_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            end_item.setForeground(QColor("#60a5fa"))
            self.table.setItem(row, 5, end_item)

            # Thời lượng
            dur_item = QTableWidgetItem(f"{item['duration']:.2f}s")
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            dur_item.setForeground(QColor("#fbbf24"))
            self.table.setItem(row, 6, dur_item)

    def on_table_row_clicked(self, item: QTableWidgetItem):
        row = item.row()
        if 0 <= row < len(self.current_timeline):
            sc = self.current_timeline[row]
            img = sc.get("image")
            if img and img.exists():
                self.lbl_status.setText(f"Cảnh {sc['id']}: {img.name} (Bắt đầu: {video_creator.format_time(sc['start'])}, Thời lượng: {sc['duration']:.2f}s)")

    # ================= TIẾN HÀNH GHÉP VIDEO =================
    def start_render(self):
        """Bắt đầu ghép video bằng FFmpeg."""
        if not self.current_timeline:
            if not self.analyze_timeline():
                return

        missing = [it for it in self.current_timeline if it["image"] is None]
        if missing:
            reply = QMessageBox.question(
                self,
                "Thiếu ảnh cho cảnh",
                f"Có {len(missing)} cảnh không tìm thấy ảnh.\nBạn có muốn tiếp tục ghép video với các ảnh sẵn có không?",
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
        aspect_ratio = self.combo_ratio.currentData() or "16:9"
        fps = int(self.combo_fps.currentData() or 30)

        self.btn_start.setEnabled(False)
        self.btn_start.setVisible(False)
        self.btn_preview.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)
        self.panel_result.setVisible(False)
        self.progress_bar.setValue(5)
        self.lbl_status.setText("Đang khởi tạo FFmpeg...")

        self.worker = VideoRenderWorker(
            timeline=self.current_timeline,
            audio_path=audio_path,
            output_path=output_path,
            total_audio_duration=self.total_audio_duration,
            aspect_ratio=aspect_ratio,
            fps=fps
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
        self.btn_start.setEnabled(True)
        self.btn_start.setVisible(True)
        self.btn_preview.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("🎉 Ghép video thành công rực rỡ!")
            if self.project:
                self.project.save_metadata()
            out_p = res.get("output_path")
            self.last_output_video = out_p
            if out_p:
                self.video_rendered.emit(str(out_p))
            dur = res.get("duration", 0.0)
            size_mb = res.get("size_mb", 0.0)
            ratio = self.combo_ratio.currentText()

            details = (
                f"• Đường dẫn: <b>{out_p}</b><br>"
                f"• Dung lượng: <b>{size_mb:.2f} MB</b> | Thời lượng: <b>{video_creator.format_time(dur)}</b> ({dur:.2f}s)<br>"
                f"• Định dạng: <b>MP4 H.264 / AAC</b> | Tỉ lệ: <b>{ratio}</b>"
            )
            self.lbl_res_details.setText(details)
            self.panel_result.setVisible(True)

            QMessageBox.information(
                self,
                "Thành Công",
                f"🎉 Ghép video thành công!\n\nFile lưu tại:\n{out_p}\nDung lượng: {size_mb:.2f} MB\nThời lượng: {video_creator.format_time(dur)}"
            )
        else:
            err = res.get("error", "Lỗi không xác định")
            self.lbl_status.setText(f"Ghép video thất bại: {err}")
            QMessageBox.critical(self, "Ghép Video Thất Bại", f"Không thể xuất video:\n\n{err}")

    # ================= MỞ FILE & THƯ MỤC =================
    def open_video_file(self):
        if self.last_output_video and self.last_output_video.exists():
            try:
                if sys.platform.startswith("win"):
                    os.startfile(str(self.last_output_video))
                elif sys.platform == "darwin":
                    subprocess.run(["open", str(self.last_output_video)])
                else:
                    subprocess.run(["xdg-open", str(self.last_output_video)])
            except Exception as e:
                QMessageBox.warning(self, "Không thể mở", f"Lỗi mở video: {e}")

    def open_output_dir(self):
        out_dir = self.project.output_dir if self.project and self.project.output_dir.exists() else config.DOWNLOADS_DIR
        if self.last_output_video and self.last_output_video.parent.exists():
            out_dir = self.last_output_video.parent

        try:
            if sys.platform.startswith("win"):
                os.startfile(str(out_dir))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(out_dir)])
            else:
                subprocess.run(["xdg-open", str(out_dir)])
        except Exception as e:
            QMessageBox.warning(self, "Không thể mở", f"Lỗi mở thư mục: {e}")

    def copy_output_path(self):
        if self.last_output_video:
            clipboard = QApplication.clipboard()
            clipboard.setText(str(self.last_output_video))
            self.lbl_status.setText("Đã sao chép đường dẫn video vào bộ nhớ tạm (Clipboard).")

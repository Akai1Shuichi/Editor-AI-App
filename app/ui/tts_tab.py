import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QSlider, QCheckBox,
    QProgressBar, QFrame, QMessageBox, QFileDialog, QScrollArea, QTabWidget,
    QSizePolicy
)

from app import config
from app.core.vibi_client import VibiClient, VibiAPIError
from app.core.tts_credits import format_credit_summary
from app.core.standalone_state import (
    StandaloneStateStore,
    build_output_folder_name,
    resolve_new_output_folder,
)
from app.ui.voice_lookup_tab import VoiceLookupTab

class TTSWorker(QThread):
    """Worker tạo giọng nói qua Vibi API."""
    status_updated = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    task_finished = pyqtSignal(bool, str, str, str)

    def __init__(
        self,
        text: str,
        voice_id: str,
        model_id: str,
        lang_code: str,
        voice_settings: Dict[str, Any],
        export_srt: bool,
        provider: str = "elevenlabs",
        output_filename: Optional[str] = None,
        output_dir: Optional[Path] = None
    ):
        super().__init__()
        self.text = text
        self.voice_id = voice_id
        self.model_id = model_id
        self.lang_code = lang_code
        self.voice_settings = voice_settings
        self.export_srt = export_srt
        self.provider = provider
        self.output_filename = output_filename
        self.output_dir = output_dir
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        client = VibiClient()
        if not client.is_configured():
            self.task_finished.emit(False, "", "", "Chưa có Voice API Key! Vào Cài đặt để nhập Key.")
            return

        self.status_updated.emit("Đang gửi yêu cầu lên Voice API...")
        self.progress_updated.emit(15)

        chunks = VibiClient.split_long_text(self.text, max_chars=3500)
        total_chunks = len(chunks)

        last_audio = None
        last_srt = None

        try:
            for idx, chunk in enumerate(chunks, 1):
                if self._is_cancelled:
                    self.task_finished.emit(False, "", "", "Tác vụ đã bị hủy.")
                    return

                chunk_filename = self.output_filename
                if total_chunks > 1 and chunk_filename:
                    stem = Path(chunk_filename).stem
                    chunk_filename = f"{stem}_part_{idx}.mp3"

                def on_prog(task_dict):
                    status = task_dict.get("status", "pending")
                    p = task_dict.get("progress", 0)
                    chunk_info = f"Đoạn {idx}/{total_chunks}: " if total_chunks > 1 else ""
                    self.status_updated.emit(f"{chunk_info}Trạng thái '{status}' ({p}%)...")
                    base_p = int(20 + (idx - 1) * (70 / total_chunks) + (p * 0.7 / total_chunks))
                    self.progress_updated.emit(min(base_p, 90))

                audio_p, srt_p = client.generate_and_download(
                    text=chunk,
                    voice_id=self.voice_id,
                    output_filename=chunk_filename,
                    output_dir=self.output_dir,
                    model_id=self.model_id,
                    language_code=self.lang_code,
                    provider=self.provider,
                    voice_settings=self.voice_settings,
                    export_transcript=self.export_srt,
                    progress_callback=on_prog,
                    is_cancelled=lambda: self._is_cancelled
                )

                last_audio = audio_p
                last_srt = srt_p

            self.progress_updated.emit(100)
            self.status_updated.emit("Hoàn tất tạo giọng nói.")
            self.task_finished.emit(
                True,
                str(last_audio) if last_audio else "",
                str(last_srt) if last_srt else "",
                "Thành công!"
            )
        except Exception as e:
            self.task_finished.emit(False, "", "", str(e))


class VoiceSelectorComboBox(QComboBox):
    """A read-only voice selector that routes users to voice lookup."""
    lookup_requested = pyqtSignal()

    def showPopup(self) -> None:
        self.lookup_requested.emit()


class TTSTab(QWidget):
    """Tab tạo giọng ElevenLabs từ văn bản - Thiết kế gọn gàng, súc tích."""
    request_voice_lookup = pyqtSignal()
    send_to_video = pyqtSignal(str, str)
    voice_generated = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tts_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.worker: Optional[TTSWorker] = None
        self.current_audio_path: Optional[Path] = None
        self.current_srt_path: Optional[Path] = None
        self.project = None
        self.auto_save: bool = False
        self.standalone_store: Optional[StandaloneStateStore] = None
        self.standalone_output_dir: Optional[Path] = None
        self.current_run_dir: Optional[Path] = None
        self.credit_balance: Optional[int] = None
        self.voice_ids_by_provider: Dict[str, str] = {
            "elevenlabs": "",
            "minimax": "",
            "capcut": "",
        }
        self.voice_names_by_provider: Dict[str, str] = {
            "elevenlabs": "",
            "minimax": "",
            "capcut": "",
        }
        self._active_voice_provider = "elevenlabs"
        self._restoring_standalone = False
        self._standalone_save_timer: Optional[QTimer] = None

        # Trình phát audio
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.durationChanged.connect(self.on_player_duration_changed)

        self.init_ui()

    def configure_standalone(
        self, store: StandaloneStateStore, output_dir: Path
    ) -> None:
        """Configure this instance as a project-independent sidebar tool."""
        self.standalone_store = store
        self.standalone_output_dir = Path(output_dir)
        self.standalone_output_dir.mkdir(parents=True, exist_ok=True)
        self.tool_header.setVisible(True)
        self.lbl_project_badge.setVisible(False)
        self.btn_to_video.setVisible(False)
        self.output_name_controls.setVisible(True)
        self.btn_choose_output.setVisible(True)
        self.edit_output_name.setText(
            build_output_folder_name("voice", day_first=True)
        )

        self._standalone_save_timer = QTimer(self)
        self._standalone_save_timer.setSingleShot(True)
        self._standalone_save_timer.setInterval(350)
        self._standalone_save_timer.timeout.connect(self._save_standalone_state)
        self._restore_standalone_state()

        for signal in (
            self.combo_provider.currentIndexChanged,
            self.combo_voice.currentIndexChanged,
            self.combo_model.currentIndexChanged,
            self.combo_lang.currentIndexChanged,
            self.slider_st.valueChanged,
            self.slider_sim.valueChanged,
            self.slider_sp.valueChanged,
            self.chk_srt.toggled,
            self.tab_widget.currentChanged,
        ):
            signal.connect(self._schedule_standalone_save)
        self._save_standalone_state()

    def _schedule_standalone_save(self, *_args) -> None:
        if self._restoring_standalone or not self._standalone_save_timer:
            return
        self._standalone_save_timer.start()

    def _save_standalone_state(self) -> None:
        if not self.standalone_store:
            return
        self.standalone_store.save_tts(
            {
                "script": self.txt_input.toPlainText(),
                "provider": self.combo_provider.currentData() or "elevenlabs",
                "voice_id": self.current_voice_id(),
                "voice_ids": self._voice_ids_snapshot(),
                "voice_names": self._voice_names_snapshot(),
                "model": self.combo_model.currentText(),
                "language": self.combo_lang.currentText(),
                "stability": self.slider_st.value(),
                "similarity": self.slider_sim.value(),
                "speed": self.slider_sp.value(),
                "export_srt": self.chk_srt.isChecked(),
                "subtab": self.tab_widget.currentIndex(),
                "audio_path": str(self.current_audio_path or ""),
                "srt_path": str(self.current_srt_path or ""),
                "output_dir": str(self.standalone_output_dir or ""),
            }
        )

    def flush_standalone_state(self) -> None:
        """Persist any debounced edit before the application closes."""
        if self._standalone_save_timer:
            self._standalone_save_timer.stop()
        self._save_standalone_state()

    def _restore_standalone_state(self) -> None:
        state = self.standalone_store.load_tts() if self.standalone_store else {}
        if not state:
            return
        self._restoring_standalone = True
        try:
            self.txt_input.setPlainText(str(state.get("script", "")))
            self._restore_voice_ids(state)
            provider = state.get("provider", "elevenlabs")
            for index in range(self.combo_provider.count()):
                if self.combo_provider.itemData(index) == provider:
                    self.combo_provider.setCurrentIndex(index)
                    break
            self.combo_model.setCurrentText(str(state.get("model", "")))
            self.combo_lang.setCurrentText(str(state.get("language", "")))
            if "stability" in state:
                self.slider_st.setValue(int(state["stability"]))
            if "similarity" in state:
                self.slider_sim.setValue(int(state["similarity"]))
            if "speed" in state:
                self.slider_sp.setValue(int(state["speed"]))
            self.chk_srt.setChecked(bool(state.get("export_srt", True)))
            output_dir = state.get("output_dir")
            if output_dir and output_dir != config.LEGACY_TTS_DOWNLOADS_DIR:
                self.standalone_output_dir = Path(output_dir)
            self._update_output_path_label()
            self.tab_widget.blockSignals(True)
            self.tab_widget.setCurrentIndex(int(state.get("subtab", 0)))
            self.tab_widget.blockSignals(False)

            audio_path = state.get("audio_path")
            srt_path = state.get("srt_path")
            if audio_path:
                self.current_audio_path = audio_path
                self.current_srt_path = srt_path
                srt_text = f" + Phụ đề {srt_path.name}" if srt_path else ""
                self.lbl_player_file.setText(
                    f"{audio_path.name} ({audio_path.stat().st_size:,} bytes){srt_text}"
                )
                self.player.setSource(QUrl.fromLocalFile(str(audio_path)))
                self.btn_play_pause.setEnabled(True)
                self.btn_stop.setEnabled(True)
        finally:
            self._restoring_standalone = False

    def set_auto_save(self, enabled: bool):
        """Bật/tắt chế độ tự động lưu cho tab TTS."""
        self.auto_save = enabled

    def set_credit_balance(self, balance: int) -> None:
        """Update the account balance used by the live credit estimate."""
        self.credit_balance = balance
        self.on_text_changed()

    def set_project(self, project):
        """Cập nhật thông tin dự án hiện tại."""
        previous_slug = getattr(self.project, "slug", None)
        next_slug = getattr(project, "slug", None)
        if previous_slug != next_slug and hasattr(self, "txt_input"):
            self.player.stop()
            self.player.setSource(QUrl())
            self.current_audio_path = None
            self.current_srt_path = None
            self.txt_input.clear()
            self.lbl_player_file.setText("Chưa có file âm thanh")
            self.btn_play_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.btn_to_video.setEnabled(False)
            self.slider_player.setRange(0, 0)
            self.progress_bar.setValue(0)
        self.project = project
        if hasattr(self, "lbl_project_badge"):
            if project:
                self.lbl_project_badge.setVisible(False)
                self.lbl_output_path.setText(str(project.voice_dir))
                self.lbl_output_path.setToolTip(str(project.voice_dir))
                self.output_name_controls.setVisible(False)
                self.btn_choose_output.setVisible(False)
            else:
                self.lbl_project_badge.setText("📁 Chưa chọn dự án")
                self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
                self.lbl_project_badge.setVisible(True)
                if not self.standalone_store:
                    self._update_output_path_label()

        # Nạp lại dữ liệu đã lưu của dự án
        if project:
            self._hydrate_project_tts(project)

    def _hydrate_project_tts(self, project):
        """Khôi phục kịch bản, cấu hình giọng và file âm thanh đã tạo trước đó."""
        # 1. Khôi phục nội dung văn bản kịch bản
        if project.tts_script:
            self.txt_input.blockSignals(True)
            self.txt_input.setPlainText(project.tts_script)
            self.txt_input.blockSignals(False)
            self.on_text_changed()

        # 2. Khôi phục cấu hình Voice
        cfg = project.tts_settings or {}
        self._restore_voice_ids(cfg)
        if cfg:
            saved_prov = cfg.get("provider", "elevenlabs")
            for i in range(self.combo_provider.count()):
                if self.combo_provider.itemData(i) == saved_prov:
                    self.combo_provider.setCurrentIndex(i)
                    break

            if "model" in cfg:
                self.combo_model.setCurrentText(cfg["model"])
            if "lang" in cfg:
                self.combo_lang.setCurrentText(cfg["lang"])
            if "stability" in cfg:
                self.slider_st.setValue(int(cfg["stability"] * 100))
            if "similarity" in cfg:
                self.slider_sim.setValue(int(cfg["similarity"] * 100))
            if "speed" in cfg:
                self.slider_sp.setValue(int(cfg["speed"] * 100))

        # 3. Nạp lại file âm thanh và phụ đề đã có
        voice = project.get_latest_voice()
        srt = project.get_latest_srt()
        if voice and voice.exists():
            self.current_audio_path = voice
            self.current_srt_path = srt
            srt_str = f" + Phụ đề {srt.name}" if srt else ""
            self.lbl_player_file.setText(f"✓ {voice.name} ({voice.stat().st_size:,} bytes){srt_str}")
            self.player.setSource(QUrl.fromLocalFile(str(voice)))
            self.btn_play_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_to_video.setEnabled(True)
            self.lbl_status.setText("✓ Đã nạp file Voice & Phụ đề sẵn có của dự án.")

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 14)
        root_layout.setSpacing(10)

        self.tool_header = QFrame()
        self.tool_header.setObjectName("tool_header")
        self.tool_header.setMaximumHeight(72)
        header_layout = QHBoxLayout(self.tool_header)
        header_layout.setContentsMargins(0, 0, 0, 2)
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        self.tool_title = QLabel("Tạo Voice TTS")
        self.tool_title.setObjectName("tool_title")
        title_layout.addWidget(self.tool_title)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        self.tool_header.setVisible(False)
        root_layout.addWidget(self.tool_header)

        # Tab widget bên trong Tạo giọng TTS
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("tts_inner_tabs")

        # ================= SUBTAB 1: TẠO GIỌNG NÓI =================
        self.tab_tts_gen = QWidget()
        self.tab_tts_gen.setObjectName("tts_gen_page")
        self.tab_tts_gen.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tts_layout = QVBoxLayout(self.tab_tts_gen)
        tts_layout.setContentsMargins(12, 12, 12, 12)
        tts_layout.setSpacing(10)

        # 1. Khung soạn thảo văn bản
        text_top = QHBoxLayout()
        lbl_text = QLabel("Văn bản cần đọc:")
        lbl_text.setProperty("class", "section_label")
        self.lbl_credit_help = QLabel("?")
        self.lbl_credit_help.setFixedSize(18, 18)
        self.lbl_credit_help.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_credit_help.setAccessibleName("Cách tính credits")
        self.lbl_credit_help.setToolTip(
            "Cách tính credits:\n"
            "- ElevenLabs Turbo/Flash: 0.5 credits mỗi ký tự\n"
            "- ElevenLabs các model khác: 1 credit mỗi ký tự\n"
            "- MiniMax Turbo: 0.6 credits mỗi ký tự\n"
            "- MiniMax HD: 1 credit mỗi ký tự\n"
            "- CapCut: 0.01 credits mỗi ký tự"
        )
        self.lbl_credit_help.setStyleSheet(
            "color: #cbd5e1; background-color: #1c2230; "
            "border: 1px solid #64748b; border-radius: 9px; "
            "font-size: 11px; font-weight: 700;"
        )
        self.lbl_char_count = QLabel("0 chars · 0/-- credits")
        self.lbl_char_count.setStyleSheet(
            "color: #cbd5e1; font-size: 13px; font-weight: 600;"
        )

        text_top.addWidget(lbl_text)
        text_top.addSpacing(10)
        self.lbl_project_badge = QLabel("📁 Chưa chọn dự án")
        self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
        text_top.addWidget(self.lbl_project_badge)
        text_top.addStretch()
        tts_layout.addLayout(text_top)

        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Nhập văn bản cần đọc vào đây (hỗ trợ tiếng Việt và đa ngôn ngữ)...")
        self.txt_input.textChanged.connect(self.on_text_changed)
        self.txt_input.setMinimumHeight(120)
        tts_layout.addWidget(self.txt_input, stretch=2)

        credit_row = QHBoxLayout()
        credit_row.setContentsMargins(0, 0, 2, 0)
        credit_row.setSpacing(6)
        credit_row.addStretch()
        credit_row.addWidget(self.lbl_credit_help)
        credit_row.addWidget(self.lbl_char_count)
        tts_layout.addLayout(credit_row)

        # 2. Cấu hình Voice & Model (Panel gọn gàng)
        cfg_panel = QFrame()
        cfg_panel.setProperty("class", "panel")
        cfg_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cp_layout = QVBoxLayout(cfg_panel)
        cp_layout.setContentsMargins(12, 10, 12, 10)
        cp_layout.setSpacing(8)

        # Dòng 1: Nền tảng, model và ngôn ngữ
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_prov = QLabel("Nền tảng:")
        lbl_prov.setProperty("class", "section_label")
        self.combo_provider = QComboBox()
        self.combo_provider.addItem("⚡ ElevenLabs", "elevenlabs")
        self.combo_provider.addItem("🤖 MiniMax", "minimax")
        self.combo_provider.addItem("🎬 CapCut", "capcut")
        self.combo_provider.currentIndexChanged.connect(self.on_provider_changed)

        self.lbl_m = QLabel("Model:")
        self.lbl_m.setProperty("class", "section_label")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["eleven_v3", "eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"])
        self.combo_model.currentIndexChanged.connect(self.on_text_changed)

        lbl_l = QLabel("Ngôn ngữ:")
        lbl_l.setProperty("class", "section_label")
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["vi", "en", "ja", "ko", "zh", "fr", "de", "es"])

        row1.addWidget(lbl_prov)
        row1.addWidget(self.combo_provider)
        row1.addSpacing(6)
        row1.addWidget(self.lbl_m)
        row1.addWidget(self.combo_model, stretch=2)
        row1.addWidget(lbl_l)
        row1.addWidget(self.combo_lang)
        cp_layout.addLayout(row1)

        # Dòng 2: Voice ID và thao tác tra cứu
        voice_row = QHBoxLayout()
        voice_row.setSpacing(8)
        lbl_vid = QLabel("Voice ID:")
        lbl_vid.setProperty("class", "section_label")
        self.combo_voice = VoiceSelectorComboBox()
        self.combo_voice.setToolTip("Bấm để mở tab Tra cứu Voice")
        self.combo_voice.lookup_requested.connect(self.open_voice_lookup)
        self._display_selected_voice()

        voice_row.addWidget(lbl_vid)
        voice_row.addWidget(self.combo_voice, stretch=1)
        cp_layout.addLayout(voice_row)

        # Dòng 3: Sliders & Phụ đề
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        # Tham số 1 (Stability / Pitch)
        self.lbl_st = QLabel("Độ ổn định:")
        self.lbl_st.setProperty("class", "section_label")
        self.lbl_st_val = QLabel("0.50")
        self.lbl_st_val.setFixedWidth(30)
        self.slider_st = QSlider(Qt.Orientation.Horizontal)
        self.slider_st.setRange(0, 100)
        self.slider_st.setValue(int(config.DEFAULT_VIBI_STABILITY * 100))
        self.slider_st.setFixedWidth(75)
        self.slider_st.valueChanged.connect(self._on_st_slider_changed)

        # Tham số 2 (Similarity / Volume)
        self.lbl_sim = QLabel("Độ tương đồng:")
        self.lbl_sim.setProperty("class", "section_label")
        self.lbl_sim_val = QLabel("0.75")
        self.lbl_sim_val.setFixedWidth(30)
        self.slider_sim = QSlider(Qt.Orientation.Horizontal)
        self.slider_sim.setRange(0, 100)
        self.slider_sim.setValue(int(config.DEFAULT_VIBI_SIMILARITY * 100))
        self.slider_sim.setFixedWidth(75)
        self.slider_sim.valueChanged.connect(self._on_sim_slider_changed)

        # Tham số 3 (Speed)
        self.lbl_sp = QLabel("Tốc độ:")
        self.lbl_sp.setProperty("class", "section_label")
        self.lbl_sp_val = QLabel("1.00x")
        self.lbl_sp_val.setFixedWidth(38)
        self.slider_sp = QSlider(Qt.Orientation.Horizontal)
        self.slider_sp.setRange(70, 150)
        self.slider_sp.setValue(int(config.DEFAULT_VIBI_SPEED * 100))
        self.slider_sp.setFixedWidth(75)
        self.slider_sp.valueChanged.connect(self._on_sp_slider_changed)

        # SRT Checkbox
        self.chk_srt = QCheckBox("Xuất phụ đề SRT")
        self.chk_srt.setChecked(True)

        row2.addWidget(self.lbl_st)
        row2.addWidget(self.slider_st)
        row2.addWidget(self.lbl_st_val)
        row2.addSpacing(6)
        row2.addWidget(self.lbl_sim)
        row2.addWidget(self.slider_sim)
        row2.addWidget(self.lbl_sim_val)
        row2.addSpacing(6)
        row2.addWidget(self.lbl_sp)
        row2.addWidget(self.slider_sp)
        row2.addWidget(self.lbl_sp_val)
        row2.addSpacing(10)
        row2.addWidget(self.chk_srt)
        row2.addStretch()

        cp_layout.addLayout(row2)
        tts_layout.addWidget(cfg_panel)

        self.output_controls = QWidget()
        output_layout = QVBoxLayout(self.output_controls)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(6)

        self.output_name_controls = QWidget()
        output_name_row = QHBoxLayout(self.output_name_controls)
        output_name_row.setContentsMargins(0, 0, 0, 0)
        output_name_row.addWidget(QLabel("Tên voice:"))
        self.edit_output_name = QLineEdit()
        self.edit_output_name.setPlaceholderText("voice_DDMMYYYY_HHMMSS")
        output_name_row.addWidget(self.edit_output_name, stretch=1)
        self.output_name_controls.setVisible(False)
        output_layout.addWidget(self.output_name_controls)

        output_path_row = QHBoxLayout()
        output_path_row.addWidget(QLabel("Lưu tại:"))
        self.lbl_output_path = QLabel()
        self.lbl_output_path.setObjectName("output_path")
        self.lbl_output_path.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.btn_choose_output = QPushButton("Thay đổi…")
        self.btn_choose_output.setObjectName("btn_subtle")
        self.btn_choose_output.clicked.connect(self.choose_output_folder)
        self.btn_choose_output.setVisible(False)
        self.btn_open_folder = QPushButton("Mở thư mục")
        self.btn_open_folder.setObjectName("btn_subtle")
        self.btn_open_folder.clicked.connect(self.open_downloads)
        output_path_row.addWidget(self.lbl_output_path, stretch=1)
        output_path_row.addWidget(self.btn_choose_output)
        output_path_row.addWidget(self.btn_open_folder)
        output_layout.addLayout(output_path_row)
        self._update_output_path_label()
        tts_layout.addWidget(self.output_controls)

        # 3. Thanh thực thi (Action & Progress)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_start = QPushButton("Tạo Giọng Nói")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.clicked.connect(self.start_tts)

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self.cancel_tts)

        action_bar.addWidget(self.btn_start, stretch=2)
        action_bar.addWidget(self.btn_cancel, stretch=2)
        tts_layout.addLayout(action_bar)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet("color: #6b7280; font-size: 11px;")

        tts_layout.addWidget(self.progress_bar)
        tts_layout.addWidget(self.lbl_status)

        # 4. Trình phát audio gọn gàng
        player_panel = QFrame()
        player_panel.setProperty("class", "panel")
        player_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        pp_layout = QVBoxLayout(player_panel)
        pp_layout.setContentsMargins(12, 10, 12, 10)
        pp_layout.setSpacing(8)

        # Thông tin file
        p_info_bar = QHBoxLayout()
        self.lbl_player_file = QLabel("Chưa có file âm thanh")
        self.lbl_player_file.setStyleSheet("color: #9ca3af; font-size: 12px;")

        p_info_bar.addWidget(self.lbl_player_file)
        p_info_bar.addStretch()

        self.btn_to_video = QPushButton("→  Kịch Bản Cảnh")
        self.btn_to_video.setObjectName("btn_subtle")
        self.btn_to_video.setToolTip(
            "Chuyển file Voice & phụ đề SRT sang bước Kịch bản cảnh trước khi xuất video"
        )
        self.btn_to_video.setEnabled(False)
        self.btn_to_video.clicked.connect(self._on_to_video_clicked)
        p_info_bar.addWidget(self.btn_to_video)
        pp_layout.addLayout(p_info_bar)

        # Scrubber bar
        scrubber = QHBoxLayout()
        self.btn_play_pause = QPushButton("Phát")
        self.btn_play_pause.setEnabled(False)
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)

        self.btn_stop = QPushButton("Dừng")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_player)

        self.lbl_time_cur = QLabel("00:00")
        self.lbl_time_cur.setStyleSheet("font-size: 11px; color: #6b7280;")

        self.slider_player = QSlider(Qt.Orientation.Horizontal)
        self.slider_player.setRange(0, 0)
        self.slider_player.sliderMoved.connect(self.set_player_pos)

        self.lbl_time_tot = QLabel("00:00")
        self.lbl_time_tot.setStyleSheet("font-size: 11px; color: #6b7280;")

        scrubber.addWidget(self.btn_play_pause)
        scrubber.addWidget(self.btn_stop)
        scrubber.addWidget(self.lbl_time_cur)
        scrubber.addWidget(self.slider_player)
        scrubber.addWidget(self.lbl_time_tot)
        pp_layout.addLayout(scrubber)

        tts_layout.addWidget(player_panel)

        # ================= SUBTAB 2: TRA CỨU VOICE =================
        self.voice_lookup_tab = VoiceLookupTab()
        self.voice_lookup_tab.voice_picked_for_tts.connect(self.on_voice_picked_from_lookup)

        # Thêm 2 subtab vào QTabWidget
        self.tab_widget.addTab(self.tab_tts_gen, "🎙️  Tạo Giọng Nói")
        self.tab_widget.addTab(self.voice_lookup_tab, "🔍  Tra Cứu Voice")
        self.tab_widget.currentChanged.connect(self.on_subtab_changed)

        root_layout.addWidget(self.tab_widget)
        self.request_voice_lookup.connect(self.open_voice_lookup)

    def open_voice_lookup(self):
        """Chuyển sang tab tra cứu giọng nói và tự động tải nếu bảng còn trống."""
        self.tab_widget.setCurrentIndex(1)

    def on_subtab_changed(self, index: int):
        """Khi người dùng bấm sang subtab Tra cứu Voice, tự động nạp danh sách nếu chưa có."""
        if index == 1 and self.voice_lookup_tab.table.rowCount() == 0:
            if config.VIBI_API_KEY and len(config.VIBI_API_KEY.strip()) > 0:
                self.voice_lookup_tab.load_voices()

    def _on_st_slider_changed(self, v: int):
        provider = self.combo_provider.currentData() or "elevenlabs"
        self.lbl_st_val.setText(str(v) if provider in ("minimax", "capcut") else f"{v / 100.0:.2f}")

    def _on_sim_slider_changed(self, v: int):
        self.lbl_sim_val.setText(f"{v / 100.0:.2f}")

    def _on_sp_slider_changed(self, v: int):
        self.lbl_sp_val.setText(f"{v / 100.0:.2f}x")

    def current_voice_id(self) -> str:
        return str(self.combo_voice.currentData() or "").strip()

    def _voice_ids_snapshot(self) -> Dict[str, str]:
        return dict(self.voice_ids_by_provider)

    def _voice_names_snapshot(self) -> Dict[str, str]:
        return dict(self.voice_names_by_provider)

    def _display_selected_voice(self) -> None:
        voice_id = self.voice_ids_by_provider.get(self._active_voice_provider, "")
        voice_name = self.voice_names_by_provider.get(self._active_voice_provider, "")
        self.combo_voice.blockSignals(True)
        self.combo_voice.clear()
        self.combo_voice.addItem(voice_name or "Chọn giọng nói…", voice_id)
        self.combo_voice.blockSignals(False)

    def _restore_voice_ids(self, settings: Dict[str, Any]) -> None:
        restored = {
            "elevenlabs": "",
            "minimax": "",
            "capcut": "",
        }
        restored_names = {provider: "" for provider in restored}
        saved_voice_ids = settings.get("voice_ids")
        if isinstance(saved_voice_ids, dict):
            for provider in restored:
                value = saved_voice_ids.get(provider)
                if value is not None:
                    restored[provider] = str(value).strip()

        saved_voice_names = settings.get("voice_names")
        if isinstance(saved_voice_names, dict):
            for provider in restored_names:
                value = saved_voice_names.get(provider)
                if value is not None:
                    restored_names[provider] = str(value).strip()

        saved_provider = str(settings.get("provider", "elevenlabs"))
        if "voice_id" in settings and not (
            isinstance(saved_voice_ids, dict) and saved_provider in saved_voice_ids
        ):
            if saved_provider in restored:
                restored[saved_provider] = str(settings["voice_id"]).strip()

        self.voice_ids_by_provider = restored
        self.voice_names_by_provider = restored_names
        self._display_selected_voice()

    def on_provider_changed(self):
        provider = self.combo_provider.currentData() or "elevenlabs"
        self._active_voice_provider = provider
        self.combo_model.blockSignals(True)
        self.combo_lang.blockSignals(True)
        self.combo_model.clear()
        self.combo_lang.clear()

        if provider == "minimax":
            self.combo_model.addItems(["speech-2.8-hd", "speech-2.8-turbo", "speech-2.6-hd", "speech-2.6-turbo", "speech-02-hd", "speech-01-hd"])
            self.combo_lang.addItems(["Vietnamese", "English", "Chinese (Mandarin)", "Japanese", "French", "German", "Spanish"])

        elif provider == "capcut":
            self.combo_model.addItems(["capcut"])
            self.combo_lang.addItems(["vi", "en", "zh", "id", "es", "pt", "ja", "th"])

        else:
            # ElevenLabs
            self.combo_model.addItems(["eleven_v3", "eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"])
            self.combo_lang.addItems(["vi", "en", "ja", "ko", "zh", "fr", "de", "es"])

        is_elevenlabs = provider == "elevenlabs"
        is_minimax = provider == "minimax"
        is_capcut = provider == "capcut"

        self.lbl_m.setVisible(not is_capcut)
        self.combo_model.setVisible(not is_capcut)

        self.lbl_st.setText("Độ ổn định:" if is_elevenlabs else "Cao độ:")
        if is_elevenlabs:
            self.slider_st.setRange(0, 100)
            self.slider_st.setValue(int(config.DEFAULT_VIBI_STABILITY * 100))
        else:
            self.slider_st.setRange(-12, 12)
            self.slider_st.setValue(0)

        self.lbl_sim.setVisible(not is_capcut)
        self.slider_sim.setVisible(not is_capcut)
        self.lbl_sim_val.setVisible(not is_capcut)
        if is_elevenlabs:
            self.lbl_sim.setText("Độ tương đồng:")
            self.slider_sim.setRange(0, 100)
            self.slider_sim.setValue(int(config.DEFAULT_VIBI_SIMILARITY * 100))
        elif is_minimax:
            self.lbl_sim.setText("Âm lượng:")
            self.slider_sim.setRange(0, 100)
            self.slider_sim.setValue(100)

        self.slider_sp.setRange(70, 150)
        self.slider_sp.setValue(int(config.DEFAULT_VIBI_SPEED * 100))

        self.combo_model.blockSignals(False)
        self.combo_lang.blockSignals(False)
        self._display_selected_voice()
        self.on_text_changed()

    def on_voice_picked_from_lookup(self, voice_id: str, voice_name: str, provider: str = "elevenlabs", language_code: str = "vi"):
        """Khi chọn dùng giọng từ thư viện, tự động thiết lập Provider, Voice ID và chuyển về tab Tạo giọng."""
        # Đổi provider nếu khác
        for i in range(self.combo_provider.count()):
            if self.combo_provider.itemData(i) == provider:
                self.combo_provider.setCurrentIndex(i)
                break

        # Gán Voice ID
        self.set_selected_voice_id(voice_id, voice_name)

        # Chọn ngôn ngữ phù hợp nếu có trong danh sách
        for i in range(self.combo_lang.count()):
            txt = self.combo_lang.itemText(i)
            if txt.lower() == language_code.lower() or language_code.lower() in txt.lower():
                self.combo_lang.setCurrentIndex(i)
                break

        self.tab_widget.setCurrentIndex(0)

    def on_text_changed(self, *_args):
        t = self.txt_input.toPlainText()
        provider = self.combo_provider.currentData() or "elevenlabs"
        model = self.combo_model.currentText()
        self.lbl_char_count.setText(
            format_credit_summary(t, provider, model, self.credit_balance)
        )
        if self.auto_save and self.project:
            self.project.tts_script = t
            self.project.save_metadata()
        self._schedule_standalone_save()

    def set_selected_voice_id(self, voice_id: str, voice_name: Optional[str] = None):
        self.voice_ids_by_provider[self._active_voice_provider] = voice_id.strip()
        self.voice_names_by_provider[self._active_voice_provider] = (voice_name or "").strip()
        self._display_selected_voice()

    def start_tts(self):
        text = self.txt_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa nhập văn bản", "Vui lòng nhập văn bản cần chuyển thành giọng nói!")
            return

        voice_id = self.current_voice_id()
        if not voice_id:
            QMessageBox.warning(self, "Thiếu Voice ID", "Vui lòng chọn hoặc nhập Voice ID!")
            return

        provider = self.combo_provider.currentData() or "elevenlabs"
        model = self.combo_model.currentText()
        lang = self.combo_lang.currentText()

        if provider == "minimax":
            settings = {
                "speed": self.slider_sp.value() / 100.0,
                "pitch": self.slider_st.value(),
                "vol": self.slider_sim.value() / 100.0
            }
        elif provider == "capcut":
            settings = {
                "speed": self.slider_sp.value() / 100.0,
                "pitch": self.slider_st.value()
            }
        else:
            settings = {
                "stability": self.slider_st.value() / 100.0,
                "similarity_boost": self.slider_sim.value() / 100.0,
                "speed": self.slider_sp.value() / 100.0
            }

        output_filename = "voice.mp3"
        if self.standalone_store:
            try:
                out_dir = resolve_new_output_folder(
                    self.standalone_output_dir or config.TTS_DOWNLOADS_DIR,
                    self.edit_output_name.text(),
                )
                out_dir.mkdir(parents=True)
            except (ValueError, OSError) as exc:
                QMessageBox.warning(self, "Không thể tạo thư mục", str(exc))
                return
            self.current_run_dir = out_dir
            output_filename = f"{out_dir.name}.mp3"
            self.output_controls.setEnabled(False)
        else:
            out_dir = self.project.voice_dir if self.project else None

        self.btn_start.setEnabled(False)
        self.btn_start.setVisible(False)
        self.btn_cancel.setEnabled(True)
        self.btn_cancel.setVisible(True)
        self.progress_bar.setValue(10)
        self.lbl_status.setText(f"Đang kết nối Voice API ({provider.upper()})...")

        self.worker = TTSWorker(
            text=text,
            voice_id=voice_id,
            model_id=model,
            lang_code=lang,
            voice_settings=settings,
            export_srt=self.chk_srt.isChecked(),
            provider=provider,
            output_filename=output_filename,
            output_dir=out_dir
        )
        self.worker.status_updated.connect(self.lbl_status.setText)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.task_finished.connect(self.on_tts_finished)
        self.worker.start()

    def cancel_tts(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.lbl_status.setText("Đang dừng tác vụ...")
            self.btn_cancel.setEnabled(False)

    def on_tts_finished(self, success: bool, audio_path: str, srt_path: str, msg: str):
        self.btn_start.setEnabled(True)
        self.btn_start.setVisible(True)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setVisible(False)
        if self.standalone_store:
            self.output_controls.setEnabled(True)

        if success:
            self.lbl_status.setText("Tạo giọng thành công.")
            if self.project:
                provider = self.combo_provider.currentData() or "elevenlabs"
                self.project.save_tts_data(
                    self.txt_input.toPlainText(),
                    {
                        "provider": provider,
                        "voice_id": self.current_voice_id(),
                        "voice_ids": self._voice_ids_snapshot(),
                        "voice_names": self._voice_names_snapshot(),
                        "model": self.combo_model.currentText(),
                        "lang": self.combo_lang.currentText(),
                        "speed": self.slider_sp.value() / 100.0,
                        "stability": self.slider_st.value() / 100.0,
                        "similarity": self.slider_sim.value() / 100.0
                    }
                )
            p = Path(audio_path)
            self.current_audio_path = p

            # Đảm bảo nhận diện file phụ đề .srt tương ứng
            resolved_srt: Optional[Path] = None
            if srt_path and Path(srt_path).exists():
                resolved_srt = Path(srt_path)
            elif p.with_suffix(".srt").exists():
                resolved_srt = p.with_suffix(".srt")
            elif self.project:
                proj_srt = self.project.get_latest_srt()
                if proj_srt and proj_srt.exists():
                    resolved_srt = proj_srt

            self.current_srt_path = resolved_srt
            srt_str = f" + Phụ đề {resolved_srt.name}" if resolved_srt else ""
            self.lbl_player_file.setText(f"{p.name} ({p.stat().st_size:,} bytes){srt_str}")

            self.player.setSource(QUrl.fromLocalFile(str(p)))
            self.btn_play_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_play_pause.setText("Phát")
            self.btn_to_video.setEnabled(True)

            # Tự động cập nhật sang tab xuất video ngay khi tạo xong
            srt_param = str(resolved_srt.resolve()) if resolved_srt else ""
            self.voice_generated.emit(str(p.resolve()), srt_param)
            self._save_standalone_state()
            if self.standalone_store:
                self.edit_output_name.setText(
                    build_output_folder_name("voice", day_first=True)
                )
        else:
            if self.standalone_store and self.current_run_dir:
                try:
                    self.current_run_dir.rmdir()
                except OSError:
                    self.edit_output_name.setText(
                        build_output_folder_name("voice", day_first=True)
                    )
                else:
                    self.current_run_dir = None
            # Phân biệt hủy vs lỗi thực sự
            is_cancelled = "hủy" in msg.lower() or "cancelled" in msg.lower()
            if is_cancelled:
                self.lbl_status.setText("Đã hủy tác vụ tạo giọng nói.")
                self.progress_bar.setValue(0)
            else:
                self.lbl_status.setText(f"Lỗi: {msg}")
                self.progress_bar.setValue(0)
                QMessageBox.critical(self, "Lỗi tạo giọng", msg)

    def _on_to_video_clicked(self):
        if self.current_audio_path:
            srt_p = str(self.current_srt_path) if self.current_srt_path else ""
            if not srt_p and self.current_audio_path.with_suffix(".srt").exists():
                srt_p = str(self.current_audio_path.with_suffix(".srt").resolve())
            self.send_to_video.emit(str(self.current_audio_path), srt_p)

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play_pause.setText("Tiếp tục")
        else:
            self.player.play()
            self.btn_play_pause.setText("Tạm dừng")

    def stop_player(self):
        self.player.stop()
        self.btn_play_pause.setText("Phát")

    def set_player_pos(self, pos: int):
        self.player.setPosition(pos)

    def on_player_position_changed(self, pos: int):
        self.slider_player.setValue(pos)
        self.lbl_time_cur.setText(self.fmt(pos))

    def on_player_duration_changed(self, dur: int):
        self.slider_player.setRange(0, dur)
        self.lbl_time_tot.setText(self.fmt(dur))

    @staticmethod
    def fmt(ms: int) -> str:
        sec = (ms // 1000) % 60
        mins = (ms // 60000)
        return f"{mins:02d}:{sec:02d}"

    def open_downloads(self):
        if self.project and self.project.voice_dir.exists():
            target = self.project.voice_dir
        elif self.current_run_dir:
            target = self.current_run_dir
        elif self.standalone_output_dir:
            target = self.standalone_output_dir
        else:
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

    def choose_output_folder(self):
        initial = self.standalone_output_dir or config.TTS_DOWNLOADS_DIR
        folder = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục lưu Voice TTS", str(initial)
        )
        if folder:
            self.standalone_output_dir = Path(folder)
            self.current_run_dir = None
            self._update_output_path_label()
            self._save_standalone_state()

    def _update_output_path_label(self) -> None:
        path = str(self.standalone_output_dir or config.TTS_DOWNLOADS_DIR)
        self.lbl_output_path.setText(path)
        self.lbl_output_path.setToolTip(path)

    def save_current_state(self):
        """Lưu lại nội dung text và cấu hình voice hiện tại vào dự án."""
        if self.project:
            provider = self.combo_provider.currentData() or "elevenlabs"
            self.project.save_tts_data(
                self.txt_input.toPlainText(),
                {
                    "provider": provider,
                    "voice_id": self.current_voice_id(),
                    "voice_ids": self._voice_ids_snapshot(),
                    "voice_names": self._voice_names_snapshot(),
                    "model": self.combo_model.currentText(),
                    "lang": self.combo_lang.currentText(),
                    "speed": self.slider_sp.value() / 100.0,
                    "stability": self.slider_st.value() / 100.0,
                    "similarity": self.slider_sim.value() / 100.0
                }
            )

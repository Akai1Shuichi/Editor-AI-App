import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QLineEdit, QPushButton, QComboBox, QSlider, QCheckBox,
    QProgressBar, QFrame, QMessageBox, QScrollArea, QTabWidget
)

from app import config
from app.core.vibi_client import VibiClient, VibiAPIError
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


class TTSTab(QWidget):
    """Tab tạo giọng ElevenLabs từ văn bản - Thiết kế gọn gàng, súc tích."""
    request_voice_lookup = pyqtSignal()
    send_to_video = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tts_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.worker: Optional[TTSWorker] = None
        self.current_audio_path: Optional[Path] = None
        self.current_srt_path: Optional[Path] = None
        self.project = None

        # Trình phát audio
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.85)

        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.durationChanged.connect(self.on_player_duration_changed)

        self.init_ui()

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
            else:
                self.lbl_project_badge.setText("📁 Chưa chọn dự án")
                self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
                self.lbl_project_badge.setVisible(True)

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 14)
        root_layout.setSpacing(10)

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
        self.lbl_char_count = QLabel("0 ký tự")
        self.lbl_char_count.setStyleSheet("color: #6b7280; font-size: 11px;")

        text_top.addWidget(lbl_text)
        text_top.addSpacing(10)
        self.lbl_project_badge = QLabel("📁 Chưa chọn dự án")
        self.lbl_project_badge.setStyleSheet("color: #6b7280; font-size: 11px;")
        text_top.addWidget(self.lbl_project_badge)
        text_top.addStretch()
        text_top.addWidget(self.lbl_char_count)
        tts_layout.addLayout(text_top)

        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Nhập văn bản cần đọc vào đây (hỗ trợ tiếng Việt và đa ngôn ngữ)...")
        self.txt_input.textChanged.connect(self.on_text_changed)
        self.txt_input.setMinimumHeight(120)
        tts_layout.addWidget(self.txt_input, stretch=2)

        # 2. Cấu hình Voice & Model (Panel gọn gàng)
        cfg_panel = QFrame()
        cfg_panel.setProperty("class", "panel")
        cfg_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        cp_layout = QVBoxLayout(cfg_panel)
        cp_layout.setContentsMargins(12, 10, 12, 10)
        cp_layout.setSpacing(8)

        # Dòng 1: Provider & Voice ID & Model & Ngôn ngữ
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        lbl_prov = QLabel("Nền tảng:")
        lbl_prov.setProperty("class", "section_label")
        self.combo_provider = QComboBox()
        self.combo_provider.addItem("⚡ ElevenLabs", "elevenlabs")
        self.combo_provider.addItem("🤖 MiniMax", "minimax")
        self.combo_provider.addItem("🎬 CapCut", "capcut")
        self.combo_provider.currentIndexChanged.connect(self.on_provider_changed)

        lbl_vid = QLabel("Voice ID:")
        lbl_vid.setProperty("class", "section_label")
        self.edit_voice_id = QLineEdit(config.DEFAULT_VIBI_VOICE_ID)
        self.edit_voice_id.setPlaceholderText("ID giọng nói...")

        self.btn_browse = QPushButton("🔍 Tra cứu Voice...")
        self.btn_browse.clicked.connect(self.open_voice_lookup)

        lbl_m = QLabel("Model:")
        lbl_m.setProperty("class", "section_label")
        self.combo_model = QComboBox()
        self.combo_model.addItems(["eleven_v3", "eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"])

        lbl_l = QLabel("Ngôn ngữ:")
        lbl_l.setProperty("class", "section_label")
        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["vi", "en", "ja", "ko", "zh", "fr", "de", "es"])

        row1.addWidget(lbl_prov)
        row1.addWidget(self.combo_provider)
        row1.addSpacing(6)
        row1.addWidget(lbl_vid)
        row1.addWidget(self.edit_voice_id, stretch=2)
        row1.addWidget(self.btn_browse)
        row1.addSpacing(6)
        row1.addWidget(lbl_m)
        row1.addWidget(self.combo_model)
        row1.addWidget(lbl_l)
        row1.addWidget(self.combo_lang)
        cp_layout.addLayout(row1)

        # Dòng 2: Sliders & Phụ đề
        row2 = QHBoxLayout()
        row2.setSpacing(12)

        # Tham số 1 (Stability / Pitch)
        self.lbl_st = QLabel("Stability:")
        self.lbl_st.setProperty("class", "section_label")
        self.lbl_st_val = QLabel("0.50")
        self.lbl_st_val.setFixedWidth(30)
        self.slider_st = QSlider(Qt.Orientation.Horizontal)
        self.slider_st.setRange(0, 100)
        self.slider_st.setValue(int(config.DEFAULT_VIBI_STABILITY * 100))
        self.slider_st.setFixedWidth(75)
        self.slider_st.valueChanged.connect(self._on_st_slider_changed)

        # Tham số 2 (Similarity / Volume)
        self.lbl_sim = QLabel("Similarity:")
        self.lbl_sim.setProperty("class", "section_label")
        self.lbl_sim_val = QLabel("0.75")
        self.lbl_sim_val.setFixedWidth(30)
        self.slider_sim = QSlider(Qt.Orientation.Horizontal)
        self.slider_sim.setRange(0, 100)
        self.slider_sim.setValue(int(config.DEFAULT_VIBI_SIMILARITY * 100))
        self.slider_sim.setFixedWidth(75)
        self.slider_sim.valueChanged.connect(self._on_sim_slider_changed)

        # Tham số 3 (Speed)
        self.lbl_sp = QLabel("Speed:")
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

        # 3. Thanh thực thi (Action & Progress)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self.btn_start = QPushButton("Tạo Giọng Nói")
        self.btn_start.setObjectName("btn_primary")
        self.btn_start.clicked.connect(self.start_tts)

        self.btn_cancel = QPushButton("Hủy")
        self.btn_cancel.setObjectName("btn_danger")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_tts)

        action_bar.addWidget(self.btn_start, stretch=2)
        action_bar.addWidget(self.btn_cancel)
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
        self.btn_open_folder = QPushButton("Mở thư mục")
        self.btn_open_folder.clicked.connect(self.open_downloads)

        p_info_bar.addWidget(self.lbl_player_file)
        p_info_bar.addStretch()

        self.btn_to_video = QPushButton("🎬  Ghép Video")
        self.btn_to_video.setObjectName("btn_subtle")
        self.btn_to_video.setToolTip("Chuyển file Voice & Phụ đề SRT sang tab Ghép Video")
        self.btn_to_video.setEnabled(False)
        self.btn_to_video.clicked.connect(self._on_to_video_clicked)
        p_info_bar.addWidget(self.btn_to_video)

        p_info_bar.addWidget(self.btn_open_folder)
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
        if self.voice_lookup_tab.table.rowCount() == 0 and config.VIBI_API_KEY:
            self.voice_lookup_tab.load_voices()

    def on_subtab_changed(self, index: int):
        """Khi người dùng bấm sang subtab Tra cứu Voice, tự động nạp danh sách nếu chưa có."""
        if index == 1 and self.voice_lookup_tab.table.rowCount() == 0:
            if config.VIBI_API_KEY and len(config.VIBI_API_KEY.strip()) > 0:
                self.voice_lookup_tab.load_voices()

    def _on_st_slider_changed(self, v: int):
        provider = self.combo_provider.currentData() or "elevenlabs"
        if provider in ("minimax", "capcut"):
            self.lbl_st_val.setText(f"{v:+d}" if v != 0 else "0")
        else:
            self.lbl_st_val.setText(f"{v / 100.0:.2f}")

    def _on_sim_slider_changed(self, v: int):
        provider = self.combo_provider.currentData() or "elevenlabs"
        if provider == "minimax":
            self.lbl_sim_val.setText(f"{v / 100.0:.1f}x")
        else:
            self.lbl_sim_val.setText(f"{v / 100.0:.2f}")

    def _on_sp_slider_changed(self, v: int):
        self.lbl_sp_val.setText(f"{v / 100.0:.2f}x")

    def on_provider_changed(self):
        provider = self.combo_provider.currentData() or "elevenlabs"
        self.combo_model.blockSignals(True)
        self.combo_lang.blockSignals(True)
        self.combo_model.clear()
        self.combo_lang.clear()

        if provider == "minimax":
            self.combo_model.addItems(["speech-2.8-hd", "speech-2.8-turbo", "speech-2.6-hd", "speech-2.6-turbo", "speech-02-hd", "speech-01-hd"])
            self.combo_lang.addItems(["Vietnamese", "English", "Chinese (Mandarin)", "Japanese", "French", "German", "Spanish"])
            # MiniMax: Pitch (-12..12), Volume (0.1..2.0), Speed (0.5..2.0)
            self.lbl_st.setText("Pitch:")
            self.slider_st.setRange(-12, 12)
            self.slider_st.setValue(0)
            self.lbl_st_val.setText("0")

            self.lbl_sim.setText("Volume:")
            self.slider_sim.setEnabled(True)
            self.slider_sim.setRange(10, 200)
            self.slider_sim.setValue(100)
            self.lbl_sim_val.setText("1.0x")

            self.slider_sp.setRange(50, 200)
            self.slider_sp.setValue(100)
            self.lbl_sp_val.setText("1.00x")

        elif provider == "capcut":
            self.combo_model.addItems(["capcut"])
            self.combo_lang.addItems(["vi", "en", "zh", "id", "es", "pt", "ja", "th"])
            # CapCut: Pitch (-12..12), Speed (0.5..2.0)
            self.lbl_st.setText("Pitch:")
            self.slider_st.setRange(-12, 12)
            self.slider_st.setValue(0)
            self.lbl_st_val.setText("0")

            self.lbl_sim.setText("Similarity:")
            self.slider_sim.setEnabled(False)
            self.slider_sim.setRange(0, 100)
            self.slider_sim.setValue(75)
            self.lbl_sim_val.setText("N/A")

            self.slider_sp.setRange(50, 200)
            self.slider_sp.setValue(100)
            self.lbl_sp_val.setText("1.00x")

        else:
            # ElevenLabs
            self.combo_model.addItems(["eleven_v3", "eleven_multilingual_v2", "eleven_flash_v2_5", "eleven_turbo_v2_5"])
            self.combo_lang.addItems(["vi", "en", "ja", "ko", "zh", "fr", "de", "es"])
            self.lbl_st.setText("Stability:")
            self.slider_st.setRange(0, 100)
            self.slider_st.setValue(int(config.DEFAULT_VIBI_STABILITY * 100))
            self.lbl_st_val.setText(f"{config.DEFAULT_VIBI_STABILITY:.2f}")

            self.lbl_sim.setText("Similarity:")
            self.slider_sim.setEnabled(True)
            self.slider_sim.setRange(0, 100)
            self.slider_sim.setValue(int(config.DEFAULT_VIBI_SIMILARITY * 100))
            self.lbl_sim_val.setText(f"{config.DEFAULT_VIBI_SIMILARITY:.2f}")

            self.slider_sp.setRange(70, 150)
            self.slider_sp.setValue(int(config.DEFAULT_VIBI_SPEED * 100))
            self.lbl_sp_val.setText(f"{config.DEFAULT_VIBI_SPEED:.2f}x")

        self.combo_model.blockSignals(False)
        self.combo_lang.blockSignals(False)

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

    def on_text_changed(self):
        t = self.txt_input.toPlainText()
        c = len(t)
        chunks = VibiClient.split_long_text(t, max_chars=3500) if t.strip() else []
        chunk_str = f" | {len(chunks)} đoạn" if len(chunks) > 1 else ""
        self.lbl_char_count.setText(f"{c:,} ký tự{chunk_str}")

    def set_selected_voice_id(self, voice_id: str, voice_name: Optional[str] = None):
        self.edit_voice_id.setText(voice_id)
        if voice_name:
            self.lbl_status.setText(f"✓ Đã chọn giọng: {voice_name} ({voice_id})")

    def start_tts(self):
        text = self.txt_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa nhập văn bản", "Vui lòng nhập văn bản cần chuyển thành giọng nói!")
            return

        voice_id = self.edit_voice_id.text().strip()
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
                "speed": self.slider_sp.value() / 100.0,
                "use_speaker_boost": True
            }

        self.btn_start.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress_bar.setValue(10)
        self.lbl_status.setText(f"Đang kết nối Voice API ({provider.upper()})...")

        out_dir = self.project.voice_dir if self.project else None

        self.worker = TTSWorker(
            text=text,
            voice_id=voice_id,
            model_id=model,
            lang_code=lang,
            voice_settings=settings,
            export_srt=self.chk_srt.isChecked(),
            provider=provider,
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
        self.btn_cancel.setEnabled(False)

        if success:
            self.lbl_status.setText("Tạo giọng thành công.")
            if self.project:
                self.project.save_metadata()
            p = Path(audio_path)
            self.current_audio_path = p
            self.current_srt_path = Path(srt_path) if srt_path else None
            srt_str = f" + Phụ đề {Path(srt_path).name}" if srt_path else ""
            self.lbl_player_file.setText(f"{p.name} ({p.stat().st_size:,} bytes){srt_str}")

            self.player.setSource(QUrl.fromLocalFile(str(p)))
            self.btn_play_pause.setEnabled(True)
            self.btn_stop.setEnabled(True)
            self.btn_play_pause.setText("Phát")
            self.btn_to_video.setEnabled(True)
        else:
            self.lbl_status.setText(f"Lỗi: {msg}")
            QMessageBox.critical(self, "Lỗi tạo giọng", msg)

    def _on_to_video_clicked(self):
        if self.current_audio_path:
            srt_p = str(self.current_srt_path) if self.current_srt_path else ""
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
        target = self.project.voice_dir if self.project and self.project.voice_dir.exists() else config.DOWNLOADS_DIR
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(target))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(target)])
            else:
                subprocess.run(["xdg-open", str(target)])
        except Exception as e:
            QMessageBox.warning(self, "Lỗi", f"Không thể mở thư mục: {e}")

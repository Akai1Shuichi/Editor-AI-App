from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTabWidget, QFrame, QMessageBox, QProgressBar
)

from app import config
from app.core.vibi_client import VibiClient, VibiAPIError


class VoiceLoaderThread(QThread):
    """Worker tải danh sách giọng từ Vibi API ngầm cho ElevenLabs, MiniMax, CapCut (có hỗ trợ phân trang)."""
    # (voices: list, has_more: bool, total_count: int, err_msg: str)
    loaded = pyqtSignal(list, bool, int, str)

    def __init__(
        self,
        source: str,
        search_query: str = "",
        gender: str = "all",
        lang: str = "all",
        page: int = 1,
        page_size: int = 30,
        sort: str = "trending"
    ):
        super().__init__()
        self.source = source
        self.search_query = search_query.strip()
        self.gender = gender
        self.lang = lang
        self.page = max(1, page)
        self.page_size = page_size
        self.sort = sort

    def run(self):
        client = VibiClient()
        if not client.is_configured():
            self.loaded.emit([], False, 0, "Chưa cấu hình Voice API Key! Vào Cài đặt để nhập Key.")
            return

        try:
            normalized_voices: List[Dict[str, Any]] = []
            q = self.search_query.lower()
            has_more = False
            total_count = -1

            if self.source == "elevenlabs_default":
                voices = client.list_default_voices(search=self.search_query or None, page_size=100)
                # Smart fallback: nếu người dùng gõ từ khóa tìm kiếm (ngôn ngữ, giới tính, accent...)
                # mà API mặc định ElevenLabs chỉ tìm strict name trả về 0, query all rồi lọc client-side
                if not voices and self.search_query:
                    all_voices = client.list_default_voices(search=None, page_size=100)
                    voices = [
                        v for v in all_voices
                        if q in v.get("name", "").lower()
                        or q in v.get("description", "").lower()
                        or q in (v.get("gender") or "").lower()
                        or q in (v.get("accent") or "").lower()
                        or q in (v.get("language") or "").lower()
                        or q in v.get("voice_id", "").lower()
                    ]

                if self.gender != "all":
                    voices = [v for v in voices if (v.get("gender") or "").lower() == self.gender.lower()]

                total_count = len(voices)
                start_idx = (self.page - 1) * self.page_size
                end_idx = start_idx + self.page_size
                paged_voices = voices[start_idx:end_idx]
                has_more = end_idx < total_count

                for v in paged_voices:
                    normalized_voices.append({
                        "voice_id": v.get("voice_id", ""),
                        "name": v.get("name", ""),
                        "provider": "elevenlabs",
                        "provider_display": "ElevenLabs",
                        "gender": (v.get("gender") or "-").capitalize(),
                        "language": v.get("language") or v.get("accent") or "en",
                        "preview_url": v.get("preview_url") or "",
                        "description": v.get("description") or ""
                    })

            elif self.source == "elevenlabs_shared":
                lang_code = None
                if self.lang != "all":
                    lang_code = self.lang
                elif q in ("vi", "vietnamese", "tieng viet", "tiếng việt"):
                    lang_code = "vi"
                elif q in ("en", "english", "tieng anh", "tiếng anh"):
                    lang_code = "en"

                # Shared voices sử dụng page 0-indexed
                page_api = max(0, self.page - 1)
                data = client.list_shared_voices(
                    search=self.search_query or None,
                    page_size=self.page_size,
                    page=page_api,
                    gender=self.gender if self.gender != "all" else None,
                    language=lang_code,
                    sort=self.sort
                )
                raw_voices = data.get("voices", [])
                has_more = bool(data.get("has_more", False))

                for v in raw_voices:
                    normalized_voices.append({
                        "voice_id": v.get("voice_id", ""),
                        "name": v.get("name", ""),
                        "provider": "elevenlabs",
                        "provider_display": "ElevenLabs (Shared)",
                        "gender": (v.get("gender") or "-").capitalize(),
                        "language": v.get("language") or v.get("accent") or "en",
                        "preview_url": v.get("preview_url") or "",
                        "description": v.get("description") or ""
                    })

            elif self.source == "minimax_system":
                mm_lang = None
                if self.lang == "vi":
                    mm_lang = "Vietnamese"
                elif self.lang == "en":
                    mm_lang = "English"
                elif self.lang == "zh":
                    mm_lang = "Chinese (Mandarin)"
                elif self.lang == "ja":
                    mm_lang = "Japanese"
                elif self.lang == "es":
                    mm_lang = "Spanish"
                elif self.lang == "fr":
                    mm_lang = "French"

                if not mm_lang and q:
                    if "vietnam" in q or "việt" in q or q == "vi":
                        mm_lang = "Vietnamese"
                    elif "english" in q or "anh" in q or q == "en":
                        mm_lang = "English"

                mm_gender = None
                if self.gender == "male":
                    mm_gender = "Male"
                elif self.gender == "female":
                    mm_gender = "Female"

                query_term = self.search_query if (self.search_query and not mm_lang) else self.search_query or None

                # MiniMax sử dụng page 1-indexed
                data = client.list_minimax_system_voices(
                    search=query_term,
                    page=self.page,
                    page_size=self.page_size,
                    gender=mm_gender,
                    language=mm_lang
                )
                raw_voices = data.get("voice_list", [])
                has_more = bool(data.get("has_more", False))
                total_count = data.get("total", -1)

                for v in raw_voices:
                    tags = v.get("tag_list") or []
                    gender = "-"
                    for t in tags:
                        if t.lower() in ("male", "female"):
                            gender = t
                            break
                    tag_display = ", ".join(tags) if tags else "-"

                    normalized_voices.append({
                        "voice_id": str(v.get("voice_id") or v.get("uniq_id") or ""),
                        "name": v.get("voice_name") or "",
                        "provider": "minimax",
                        "provider_display": "MiniMax",
                        "gender": gender.capitalize(),
                        "language": tag_display,
                        "preview_url": v.get("sample_audio") or "",
                        "description": v.get("description") or ""
                    })

            elif self.source == "capcut_system":
                cc_lang = None
                if self.lang != "all":
                    cc_lang = self.lang
                elif q in ("vi", "vietnamese", "tieng viet", "tiếng việt"):
                    cc_lang = "vi"
                elif q in ("en", "english", "tieng anh", "tiếng anh"):
                    cc_lang = "en"
                elif q in ("zh", "chinese"):
                    cc_lang = "zh"

                cc_gender = None
                if self.gender == "male":
                    cc_gender = "Male"
                elif self.gender == "female":
                    cc_gender = "Female"

                query_term = self.search_query or None

                # CapCut sử dụng page 1-indexed
                data = client.list_capcut_system_voices(
                    search=query_term,
                    page=self.page,
                    page_size=self.page_size,
                    language=cc_lang,
                    gender=cc_gender
                )
                raw_voices = data.get("voice_list", [])
                has_more = bool(data.get("has_more", False))
                total_count = data.get("total", -1)

                for v in raw_voices:
                    tags = v.get("tags") or []
                    tag_str = f"[{v.get('language', '-')}] " + (f"{', '.join(tags)}" if tags else "")
                    normalized_voices.append({
                        "voice_id": str(v.get("voice_id") or ""),
                        "name": v.get("name") or "",
                        "provider": "capcut",
                        "provider_display": "CapCut",
                        "gender": (v.get("gender") or "-").capitalize(),
                        "language": tag_str,
                        "preview_url": v.get("preview_url") or "",
                        "description": ", ".join(tags) if tags else ""
                    })

            elif self.source == "community_voices":
                c_lang = None
                if self.lang != "all":
                    c_lang = self.lang
                elif q in ("vi", "vietnamese", "tieng viet", "tiếng việt"):
                    c_lang = "vi"
                elif q in ("en", "english", "tieng anh", "tiếng anh"):
                    c_lang = "en"

                c_gender = None
                if self.gender == "male":
                    c_gender = "male"
                elif self.gender == "female":
                    c_gender = "female"

                offset = (self.page - 1) * self.page_size
                data = client.list_community_voices(
                    search=self.search_query or None,
                    limit=self.page_size,
                    offset=offset,
                    gender=c_gender,
                    language=c_lang
                )
                raw_voices = data.get("voices", [])
                total_count = data.get("total", -1)
                has_more = (offset + len(raw_voices)) < total_count if total_count >= 0 else False

                for v in raw_voices:
                    cats = v.get("categories") or []
                    cat_str = f"[{v.get('language', 'vi')}] " + (f"({', '.join(cats)})" if cats else "")
                    provider_raw = v.get("provider", "minimax")
                    normalized_voices.append({
                        "voice_id": str(v.get("voice_id") or ""),
                        "name": v.get("name") or "",
                        "provider": provider_raw,
                        "provider_display": f"Phổ Biến ({provider_raw.capitalize()})",
                        "gender": (v.get("gender") or "-").capitalize(),
                        "language": cat_str,
                        "preview_url": v.get("preview_url") or "",
                        "description": v.get("description") or ""
                    })

            self.loaded.emit(normalized_voices, has_more, total_count, "")
        except Exception as e:
            self.loaded.emit([], False, 0, str(e))


class VoiceLookupTab(QWidget):
    """Tab tra cứu danh sách Giọng & Voice ID cho ElevenLabs, MiniMax, CapCut có phân trang."""
    # (voice_id, voice_name, provider, language_code)
    voice_picked_for_tts = pyqtSignal(str, str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("voice_lookup_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.worker: Optional[VoiceLoaderThread] = None
        self.current_voices: List[Dict[str, Any]] = []

        # Trạng thái phân trang
        self.current_page: int = 1
        self.page_size: int = 30
        self.has_more: bool = False
        self.total_count: int = -1

        # Audio player nghe thử mẫu giọng
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.current_preview_btn: Optional[QPushButton] = None
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Thanh tìm kiếm & Bộ lọc linh hoạt
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        # Nguồn giọng
        self.combo_source = QComboBox()
        self.combo_source.addItem("🌐 Giọng Phổ Biến", "community_voices")
        self.combo_source.addItem("⚡ ElevenLabs (Mặc định)", "elevenlabs_default")
        self.combo_source.addItem("⚡ ElevenLabs (Thư viện cộng đồng)", "elevenlabs_shared")
        self.combo_source.addItem("🤖 MiniMax (Giọng hệ thống)", "minimax_system")
        self.combo_source.addItem("🎬 CapCut (Giọng hệ thống)", "capcut_system")
        self.combo_source.currentIndexChanged.connect(self.on_filter_changed)

        # Ô tìm kiếm từ khóa
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Tìm theo tên giọng, mô tả, từ khóa, Voice ID...")
        self.edit_search.returnPressed.connect(self.on_filter_changed)

        # Lọc ngôn ngữ
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Tất cả ngôn ngữ", "all")
        self.combo_lang.addItem("Tiếng Việt (vi)", "vi")
        self.combo_lang.addItem("English (en)", "en")
        self.combo_lang.addItem("Chinese (zh)", "zh")
        self.combo_lang.addItem("Japanese (ja)", "ja")
        self.combo_lang.addItem("Spanish (es)", "es")
        self.combo_lang.currentIndexChanged.connect(self.on_filter_changed)

        # Lọc giới tính
        self.combo_gender = QComboBox()
        self.combo_gender.addItem("Tất cả giới tính", "all")
        self.combo_gender.addItem("Nam (Male)", "male")
        self.combo_gender.addItem("Nữ (Female)", "female")
        self.combo_gender.currentIndexChanged.connect(self.on_filter_changed)

        # Nút tìm kiếm
        self.btn_search = QPushButton("🔍 Tìm kiếm")
        self.btn_search.setObjectName("btn_primary")
        self.btn_search.clicked.connect(self.on_filter_changed)

        top_bar.addWidget(self.combo_source)
        top_bar.addWidget(self.edit_search, stretch=2)
        top_bar.addWidget(self.combo_lang)
        top_bar.addWidget(self.combo_gender)
        top_bar.addWidget(self.btn_search)
        layout.addLayout(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Bảng hiển thị danh sách giọng (6 cột)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Nền Tảng", "Tên Giọng", "Voice ID", "Giới Tính", "Ngôn Ngữ / Thẻ", "Thao Tác"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 125)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 160)
        self.table.setColumnWidth(3, 80)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 220)
        self.table.horizontalHeader().setMinimumSectionSize(60)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.verticalHeader().setDefaultSectionSize(44)
        layout.addWidget(self.table)

        # Footer Bar: Tích hợp thông tin hiển thị & Phân trang trong một thanh chuẩn design
        self.footer_bar = QFrame()
        self.footer_bar.setObjectName("pagination_bar")
        footer_layout = QHBoxLayout(self.footer_bar)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        footer_layout.setSpacing(10)

        # Bên trái: Thông tin hiển thị / trạng thái
        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px;")

        # Bên phải: Cụm điều khiển phân trang
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        # Dropdown số giọng / trang
        self.combo_page_size = QComboBox()
        self.combo_page_size.addItem("30 / trang", 30)
        self.combo_page_size.addItem("50 / trang", 50)
        self.combo_page_size.addItem("100 / trang", 100)
        self.combo_page_size.setMaxVisibleItems(10)
        self.combo_page_size.setFixedWidth(115)
        self.combo_page_size.setFixedHeight(32)
        self.combo_page_size.currentIndexChanged.connect(self.on_page_size_changed)

        # Nút về trang đầu: «
        self.btn_first = QPushButton("«")
        self.btn_first.setToolTip("Trang đầu")
        self.btn_first.setFixedSize(32, 32)
        self.btn_first.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_first.clicked.connect(self.go_first_page)

        # Nút lùi: ‹ Trước
        self.btn_prev = QPushButton("‹ Trước")
        self.btn_prev.setFixedSize(78, 32)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.clicked.connect(self.go_prev_page)

        # Huy hiệu số trang (Page badge pill)
        self.lbl_page_info = QLabel("Trang 1")
        self.lbl_page_info.setFixedHeight(32)
        self.lbl_page_info.setMinimumWidth(85)
        self.lbl_page_info.setStyleSheet(
            "background-color: #1e2230; border: 1px solid #2e3446; "
            "border-radius: 6px; padding: 0 10px; font-weight: 600; color: #38bdf8; font-size: 12px;"
        )
        self.lbl_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Nút tiến: Sau ›
        self.btn_next = QPushButton("Sau ›")
        self.btn_next.setFixedSize(78, 32)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.clicked.connect(self.go_next_page)

        # Nút đến trang cuối: »
        self.btn_last = QPushButton("»")
        self.btn_last.setToolTip("Trang cuối")
        self.btn_last.setFixedSize(32, 32)
        self.btn_last.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_last.clicked.connect(self.go_last_page)

        nav_layout.addWidget(self.combo_page_size)
        nav_layout.addSpacing(6)
        nav_layout.addWidget(self.btn_first)
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_page_info)
        nav_layout.addWidget(self.btn_next)
        nav_layout.addWidget(self.btn_last)

        footer_layout.addWidget(self.lbl_status)
        footer_layout.addStretch()
        footer_layout.addLayout(nav_layout)

        layout.addWidget(self.footer_bar)

        self.update_pagination_ui()

    def on_filter_changed(self):
        """Khi thay đổi từ khóa tìm kiếm, bộ lọc ngôn ngữ, giới tính hoặc nguồn, reset về trang 1."""
        self.current_page = 1
        self.load_voices()

    def on_page_size_changed(self):
        self.page_size = self.combo_page_size.currentData() or 30
        self.current_page = 1
        self.load_voices()

    def go_first_page(self):
        if self.current_page > 1:
            self.current_page = 1
            self.load_voices()

    def go_prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_voices()

    def go_next_page(self):
        if self.has_more:
            self.current_page += 1
            self.load_voices()

    def go_last_page(self):
        if self.total_count > 0:
            total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
            if self.current_page < total_pages:
                self.current_page = total_pages
                self.load_voices()

    def update_pagination_ui(self):
        can_go_back = (self.current_page > 1)
        self.btn_first.setEnabled(can_go_back)
        self.btn_prev.setEnabled(can_go_back)

        if self.total_count > 0:
            total_pages = max(1, (self.total_count + self.page_size - 1) // self.page_size)
            can_go_forward = (self.current_page < total_pages)
            self.btn_next.setEnabled(can_go_forward)
            self.btn_last.setEnabled(can_go_forward)
            self.btn_last.setVisible(True)
            self.lbl_page_info.setText(f"Trang {self.current_page} / {total_pages}")
        else:
            self.btn_next.setEnabled(self.has_more)
            self.btn_last.setVisible(False)
            self.lbl_page_info.setText(f"Trang {self.current_page}")

    def load_voices(self):
        if self.worker and self.worker.isRunning():
            return

        source = self.combo_source.currentData() or "community_voices"
        search = self.edit_search.text().strip()
        gender = self.combo_gender.currentData() or "all"
        lang = self.combo_lang.currentData() or "all"

        self.stop_preview()
        self.btn_search.setEnabled(False)
        self.btn_first.setEnabled(False)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)
        self.btn_last.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText(f"Đang tải trang {self.current_page}...")

        self.worker = VoiceLoaderThread(
            source=source,
            search_query=search,
            gender=gender,
            lang=lang,
            page=self.current_page,
            page_size=self.page_size
        )
        self.worker.loaded.connect(self.on_voices_loaded)
        self.worker.start()

    def on_voices_loaded(self, voices: List[Dict[str, Any]], has_more: bool, total_count: int, err_msg: str):
        self.btn_search.setEnabled(True)
        self.progress_bar.setVisible(False)

        if err_msg:
            self.lbl_status.setText(f"Lỗi: {err_msg}")
            QMessageBox.warning(self, "Lỗi tải danh sách giọng", err_msg)
            self.update_pagination_ui()
            return

        self.current_voices = voices
        self.has_more = has_more
        self.total_count = total_count
        self.update_pagination_ui()

        self.table.setRowCount(0)

        for row, v in enumerate(voices):
            v_id = str(v.get("voice_id", ""))
            name = v.get("name", "")
            provider = v.get("provider", "elevenlabs")
            provider_disp = v.get("provider_display", provider.upper())
            gender = v.get("gender") or "-"
            lang = v.get("language") or "-"
            preview_url = v.get("preview_url") or ""

            self.table.insertRow(row)

            # Cột 0: Nền tảng
            item_prov = QTableWidgetItem(provider_disp)
            item_prov.setForeground(Qt.GlobalColor.cyan)
            item_prov.setToolTip(f"Nền tảng: {provider_disp}")
            self.table.setItem(row, 0, item_prov)

            # Cột 1: Tên Giọng
            item_name = QTableWidgetItem(name)
            item_name.setForeground(Qt.GlobalColor.white)
            desc = v.get("description")
            item_name.setToolTip(f"{name}\n{desc}" if desc else name)
            self.table.setItem(row, 1, item_name)

            # Cột 2: Voice ID
            item_id = QTableWidgetItem(v_id)
            item_id.setForeground(Qt.GlobalColor.yellow)
            item_id.setToolTip(f"Voice ID: {v_id}\n(Click nút 'Copy' để sao chép)")
            self.table.setItem(row, 2, item_id)

            # Cột 3: Giới tính
            item_gender = QTableWidgetItem(gender)
            item_gender.setToolTip(f"Giới tính: {gender}")
            self.table.setItem(row, 3, item_gender)

            # Cột 4: Ngôn ngữ / Thẻ
            item_lang = QTableWidgetItem(lang)
            item_lang.setToolTip(f"Ngôn ngữ / Thẻ:\n{lang}")
            self.table.setItem(row, 4, item_lang)

            # Cột 5: Thao tác (Nghe thử, Dùng giọng, Copy ID)
            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(4, 2, 4, 2)
            a_layout.setSpacing(4)
            a_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Nút Nghe thử
            btn_play = QPushButton("▶ Nghe")
            btn_play.setObjectName("btn_subtle")
            btn_play.setMinimumWidth(60)
            btn_play.setMaximumWidth(68)
            btn_play.setCursor(Qt.CursorShape.PointingHandCursor)
            if preview_url:
                btn_play.clicked.connect(lambda _, u=preview_url, b=btn_play: self.toggle_preview(u, b))
            else:
                btn_play.setEnabled(False)
                btn_play.setToolTip("Không có file âm thanh mẫu.")

            # Nút Dùng giọng
            btn_use = QPushButton("Dùng giọng")
            btn_use.setObjectName("btn_primary")
            btn_use.setMinimumWidth(74)
            btn_use.setMaximumWidth(82)
            btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_use.clicked.connect(lambda _, vid=v_id, vn=name, p=provider, l=lang: self.use_voice(vid, vn, p, l))

            # Nút Copy ID
            btn_copy = QPushButton("Copy")
            btn_copy.setObjectName("btn_subtle")
            btn_copy.setMinimumWidth(44)
            btn_copy.setMaximumWidth(52)
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.clicked.connect(lambda _, vid=v_id: self.copy_id(vid))

            a_layout.addWidget(btn_play)
            a_layout.addWidget(btn_use)
            a_layout.addWidget(btn_copy)

            self.table.setCellWidget(row, 5, action_widget)

        if total_count > 0:
            start_idx = (self.current_page - 1) * self.page_size + 1
            end_idx = min(start_idx + len(voices) - 1, total_count)
            self.lbl_status.setText(f"Hiển thị {start_idx}–{end_idx} trên {total_count:,} giọng • {self.combo_source.currentText()}")
        else:
            self.lbl_status.setText(f"Hiển thị {len(voices)} giọng • {self.combo_source.currentText()}")

    def toggle_preview(self, url: str, btn: QPushButton):
        """Phát hoặc dừng âm thanh nghe thử giọng nói."""
        if not url:
            return

        if self.current_preview_btn == btn and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.stop_preview()
            return

        self.stop_preview()
        self.current_preview_btn = btn
        btn.setText("⏹ Dừng")
        self.player.setSource(QUrl(url))
        self.player.play()

    def stop_preview(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.stop()
        if self.current_preview_btn:
            self.current_preview_btn.setText("▶ Nghe")
            self.current_preview_btn = None

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState:
            if self.current_preview_btn:
                self.current_preview_btn.setText("▶ Nghe")
                self.current_preview_btn = None

    def use_voice(self, voice_id: str, voice_name: str, provider: str, language: str):
        # Xác định mã ngôn ngữ phù hợp cho TTS
        lang_code = "vi"
        if provider == "minimax":
            lang_code = "Vietnamese" if "vietnam" in language.lower() or "vi" in language.lower() else "English"
        elif provider in ("elevenlabs", "capcut"):
            lang_code = "vi" if "vi" in language.lower() else "en"

        self.stop_preview()
        self.voice_picked_for_tts.emit(voice_id, voice_name, provider, lang_code)

    def copy_id(self, text: str):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self.lbl_status.setText(f"Đã sao chép Voice ID: {text}")

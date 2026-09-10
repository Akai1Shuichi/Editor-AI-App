from typing import Optional, List, Dict, Any

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTabWidget, QFrame, QMessageBox, QProgressBar
)

from app import config
from app.core.vibi_client import VibiClient, VibiAPIError

class VoiceLoaderThread(QThread):
    """Worker tải danh sách giọng từ Vibi API ngầm."""
    loaded = pyqtSignal(list, str)

    def __init__(self, mode: str, search_query: str = "", gender: str = "all", sort: str = "trending"):
        super().__init__()
        self.mode = mode
        self.search_query = search_query
        self.gender = gender
        self.sort = sort

    def run(self):
        client = VibiClient()
        if not client.is_configured():
            self.loaded.emit([], "Chưa cấu hình Voice API Key! Vào Cài đặt để nhập Key.")
            return

        try:
            if self.mode == "default":
                voices = client.list_default_voices(search=self.search_query or None, page_size=60)
                self.loaded.emit(voices, "")
            else:
                data = client.list_shared_voices(
                    search=self.search_query or None,
                    page_size=40,
                    gender=self.gender if self.gender != "all" else None,
                    sort=self.sort
                )
                voices = data.get("voices", [])
                self.loaded.emit(voices, "")
        except Exception as e:
            self.loaded.emit([], str(e))


class VoiceLookupTab(QWidget):
    """Tab tra cứu danh sách Giọng & Voice ID - Giao diện tinh gọn, trực quan."""
    voice_picked_for_tts = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("voice_lookup_tab")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.worker: Optional[VoiceLoaderThread] = None
        self.current_voices: List[Dict[str, Any]] = []
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Thanh tìm kiếm & Phân loại gọn gàng
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.combo_category = QComboBox()
        self.combo_category.addItems(["Giọng Mặc Định (Default)", "Thư Viện Cộng Đồng (Shared)"])
        self.combo_category.currentIndexChanged.connect(self.on_category_changed)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Tìm kiếm theo tên giọng, ngôn ngữ...")
        self.edit_search.returnPressed.connect(self.load_voices)

        self.combo_gender = QComboBox()
        self.combo_gender.addItems(["Tất cả giới tính", "Nam (Male)", "Nữ (Female)"])
        self.combo_gender.setEnabled(False)
        self.combo_gender.currentIndexChanged.connect(self.load_voices)

        self.btn_search = QPushButton("Tìm kiếm")
        self.btn_search.setObjectName("btn_primary")
        self.btn_search.clicked.connect(self.load_voices)

        top_bar.addWidget(self.combo_category)
        top_bar.addWidget(self.edit_search, stretch=2)
        top_bar.addWidget(self.combo_gender)
        top_bar.addWidget(self.btn_search)
        layout.addLayout(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Bảng hiển thị danh sách giọng
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Tên Giọng", "Voice ID", "Giới Tính", "Ngôn Ngữ / Accent", "Thao Tác"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 85)
        self.table.setColumnWidth(4, 260)
        self.table.verticalHeader().setDefaultSectionSize(42)
        layout.addWidget(self.table)

        # Status footer
        self.lbl_status = QLabel("Nhấn 'Tìm kiếm' để tải danh sách giọng từ Voice API.")
        self.lbl_status.setStyleSheet("color: #6b7280; font-size: 11px;")
        layout.addWidget(self.lbl_status)

    def on_category_changed(self, index: int):
        self.combo_gender.setEnabled(index == 1)
        self.load_voices()

    def load_voices(self):
        is_default = (self.combo_category.currentIndex() == 0)
        mode = "default" if is_default else "shared"
        search = self.edit_search.text().strip()

        gender_raw = self.combo_gender.currentText()
        gender = "male" if "Nam" in gender_raw else ("female" if "Nữ" in gender_raw else "all")

        self.btn_search.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.lbl_status.setText("Đang tải dữ liệu từ Voice API...")

        self.worker = VoiceLoaderThread(mode=mode, search_query=search, gender=gender)
        self.worker.loaded.connect(self.on_voices_loaded)
        self.worker.start()

    def on_voices_loaded(self, voices: List[Dict[str, Any]], err_msg: str):
        self.btn_search.setEnabled(True)
        self.progress_bar.setVisible(False)

        if err_msg:
            self.lbl_status.setText(f"Lỗi: {err_msg}")
            QMessageBox.warning(self, "Lỗi tải giọng", err_msg)
            return

        self.current_voices = voices
        self.table.setRowCount(0)

        for row, v in enumerate(voices):
            v_id = v.get("voice_id", "")
            name = v.get("name", "")
            gender = v.get("gender") or "-"
            accent = v.get("accent") or v.get("language") or "-"

            self.table.insertRow(row)

            # Tên
            item_name = QTableWidgetItem(name)
            item_name.setForeground(Qt.GlobalColor.white)
            self.table.setItem(row, 0, item_name)

            # Voice ID
            item_id = QTableWidgetItem(v_id)
            item_id.setForeground(Qt.GlobalColor.yellow)
            self.table.setItem(row, 1, item_id)

            # Giới tính
            self.table.setItem(row, 2, QTableWidgetItem(gender))

            # Ngôn ngữ
            self.table.setItem(row, 3, QTableWidgetItem(accent))

            # Action buttons
            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(6, 4, 6, 4)
            a_layout.setSpacing(6)
            a_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            btn_use = QPushButton("Dùng giọng")
            btn_use.setObjectName("btn_primary")
            btn_use.setMinimumWidth(84)
            btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_use.clicked.connect(lambda _, vid=v_id, vn=name: self.use_voice(vid, vn))

            btn_copy = QPushButton("Copy ID")
            btn_copy.setObjectName("btn_subtle")
            btn_copy.setMinimumWidth(64)
            btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_copy.clicked.connect(lambda _, vid=v_id: self.copy_id(vid))

            btn_def = QPushButton("Mặc định")
            btn_def.setObjectName("btn_subtle")
            btn_def.setMinimumWidth(72)
            btn_def.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_def.clicked.connect(lambda _, vid=v_id: self.set_default(vid))

            a_layout.addWidget(btn_use)
            a_layout.addWidget(btn_copy)
            a_layout.addWidget(btn_def)

            self.table.setCellWidget(row, 4, action_widget)

        self.lbl_status.setText(f"Tìm thấy {len(voices)} giọng.")

    def use_voice(self, voice_id: str, voice_name: str):
        self.voice_picked_for_tts.emit(voice_id, voice_name)

    def copy_id(self, text: str):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
        self.lbl_status.setText(f"Đã sao chép Voice ID: {text}")

    def set_default(self, voice_id: str):
        config.save_env_variable("DEFAULT_VIBI_VOICE_ID", voice_id)
        config.DEFAULT_VIBI_VOICE_ID = voice_id
        self.lbl_status.setText(f"Đã lưu Voice ID mặc định: {voice_id}")

"""
Minimalist & Professional Dark Theme for PyQt6.
Design Principles:
- High contrast, clean hierarchy, neutral dark tones.
- No flashy gradients or redundant nested borders.
- Crisp typography, consistent spacing, intuitive controls.
"""

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication

DARK_THEME_QSS = """
/* ================= GLOBAL RESETS ================= */
* {
    font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
    font-size: 13px;
    color: #e5e7eb;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #121316;
}

/* ================= TOOLTIP ================= */
QToolTip {
    background-color: #1e2029;
    color: #f8fafc;
    border: 1px solid #3b82f6;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}

#central_widget, #content_container, QStackedWidget, QSplitter {
    background-color: #121316;
}

QWidget#central_widget, QWidget#content_container {
    background-color: #121316;
}

#watermark_tab, #tts_tab, #voice_lookup_tab, #scene_tab, #video_tab, #project_tab, #settings_tab, #pricing_tab {
    background-color: #121316;
}

QFrame#update_bar {
    background-color: #16171d;
    border-bottom: 1px solid #23252c;
}

QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {
    background-color: #121316;
    border: none;
}

/* ================= SCROLLBAR ================= */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2d2f38;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #3f424e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background: #2d2f38;
    min-width: 20px;
    border-radius: 3px;
}

QScrollBar::handle:horizontal:hover {
    background: #3f424e;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* ================= SIDEBAR ================= */
#sidebar {
    background-color: #16171d;
    border-right: 1px solid #23252c;
    min-width: 260px;
    max-width: 260px;
}

#sidebar_brand {
    padding: 16px 14px 12px 14px;
}

#app_logo {
    font-size: 15px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.3px;
}

#app_tagline {
    font-size: 11px;
    color: #6b7280;
    margin-top: 2px;
}

#nav_btn {
    text-align: left;
    padding: 9px 12px;
    font-size: 13px;
    font-weight: 500;
    color: #9ca3af;
    background-color: transparent;
    border: none;
    border-radius: 6px;
    margin: 2px 8px;
}

#nav_btn:hover {
    background-color: #1f2028;
    color: #f3f4f6;
}

#nav_btn:checked {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
}

#sidebar_footer {
    padding: 12px 14px;
    border-top: 1px solid #23252c;
}

#sidebar_version {
    color: #70798a;
    font-size: 11px;
    font-weight: 600;
}

QTabWidget#workspace_pages::pane {
    border: none;
}

#app_footer {
    background-color: #172033;
    border-top: 2px solid #2563eb;
}

/* ================= STANDALONE TOOL HEADER ================= */
#tool_header {
    background-color: transparent;
    border-bottom: 1px solid #23252c;
    padding-bottom: 10px;
}

#tool_title {
    color: #f8fafc;
    font-size: 20px;
    font-weight: 700;
}

#tool_subtitle {
    color: #7f8a9d;
    font-size: 12px;
}

#save_state {
    color: #34d399;
    background-color: #10251f;
    border: 1px solid #1d493b;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 11px;
    font-weight: 600;
}

#output_path {
    color: #8b95a7;
    font-size: 11px;
}

/* ================= API KEY PURCHASE OFFER ================= */
#pricing_offer {
    background-color: #172033;
    border: 1px solid #29466f;
    border-radius: 7px;
}

#offer_label {
    color: #f8fafc;
    font-size: 12px;
    font-weight: 600;
}

#offer_sale {
    color: #fbbf24;
    background-color: #3a2b0d;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: 700;
}

#offer_old_price {
    color: #94a3b8;
    font-size: 12px;
    text-decoration: line-through;
}

#offer_price {
    color: #34d399;
    font-size: 16px;
    font-weight: 700;
}

#bot_purchase_link, #zalo_purchase_link {
    color: #93c5fd;
    font-size: 12px;
    font-weight: 700;
}

/* ================= TOP BAR ================= */
#top_bar {
    background-color: #16171d;
    border-bottom: 1px solid #23252c;
    padding: 10px 20px;
    min-height: 28px;
}

#page_title {
    font-size: 15px;
    font-weight: 600;
    color: #f9fafb;
}

#api_chip {
    background-color: #1a202c;
    border: 1px solid #2d3748;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 500;
    color: #94a3b8;
}

/* ================= CARDS / PANELS ================= */
.panel {
    background-color: #181920;
    border: 1px solid #252730;
    border-radius: 8px;
    padding: 14px;
}

.panel_title {
    font-size: 13px;
    font-weight: 600;
    color: #e5e7eb;
    margin-bottom: 6px;
}

.section_label {
    font-size: 12px;
    font-weight: 500;
    color: #9ca3af;
}

/* Drop Area */
#drop_area {
    border: 1px dashed #374151;
    border-radius: 8px;
    background-color: #15161c;
}

#drop_area:hover {
    border-color: #3b82f6;
    background-color: #181a24;
}

#preview_frame {
    background-color: #131419;
    border: 1px solid #252730;
    border-radius: 6px;
}

/* ================= INPUTS & FORMS ================= */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #14151a;
    border: 1px solid #282a33;
    border-radius: 6px;
    padding: 7px 10px;
    color: #f3f4f6;
    selection-background-color: #2563eb;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
    background-color: #16171f;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #101114;
    border-color: #1f2026;
    color: #4b5563;
}

QComboBox {
    background-color: #14151a;
    border: 1px solid #282a33;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f3f4f6;
    min-height: 20px;
}

QComboBox:hover {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #181920;
    border: 1px solid #2d303b;
    border-radius: 6px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    padding: 4px;
    outline: none;
}

QComboBox QAbstractItemView::item {
    min-height: 30px;
    padding: 4px 10px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #262937;
    color: #ffffff;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}

/* ================= BUTTONS ================= */
QPushButton {
    background-color: #1e2029;
    border: 1px solid #2d303b;
    border-radius: 6px;
    padding: 7px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #e5e7eb;
}

QPushButton:hover {
    background-color: #262934;
    border-color: #3b3f4e;
    color: #ffffff;
}

QPushButton:pressed {
    background-color: #1a1c24;
}

QPushButton:disabled {
    background-color: #14151a;
    border-color: #1f2028;
    color: #4b5563;
}

QPushButton#btn_primary {
    background-color: #2563eb;
    border: 1px solid #1d4ed8;
    color: #ffffff;
    font-weight: 600;
}

QPushButton#btn_primary:hover {
    background-color: #1d4ed8;
}

QPushButton#btn_primary:pressed {
    background-color: #1e40af;
}

QPushButton#btn_tutorial {
    background-color: #291b20;
    border: 1px solid #8f3c48;
    color: #ffe4e6;
    font-weight: 700;
    padding: 7px 12px;
}

QPushButton#btn_tutorial:hover {
    background-color: #412128;
    border-color: #ef4444;
    color: #ffffff;
}

QPushButton#btn_tutorial:pressed {
    background-color: #5b2630;
}

QPushButton#btn_buy_api {
    background-color: #2563eb;
    border: 1px solid #1d4ed8;
    color: #ffffff;
    font-weight: 700;
}

QPushButton#btn_buy_api:hover {
    background-color: #1d4ed8;
    border-color: #1e40af;
}

QPushButton#btn_danger {
    background-color: #2d181b;
    border: 1px solid #4c1d24;
    color: #f87171;
}

QPushButton#btn_danger:hover {
    background-color: #3b1c20;
}

QPushButton#btn_subtle {
    background-color: transparent;
    border: 1px solid #282a33;
    color: #9ca3af;
}

QPushButton#btn_subtle:hover {
    background-color: #1a1c22;
    color: #e5e7eb;
}

/* ================= SLIDERS ================= */
QSlider::groove:horizontal {
    height: 4px;
    background: #252732;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #f9fafb;
    width: 14px;
    height: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #93c5fd;
}

/* ================= PROGRESS BAR ================= */
QProgressBar {
    background-color: #14151a;
    border: 1px solid #252730;
    border-radius: 4px;
    text-align: center;
    color: #e5e7eb;
    font-size: 11px;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 3px;
}

/* ================= TABLES ================= */
QTableWidget {
    background-color: #14151a;
    border: 1px solid #23252c;
    border-radius: 6px;
    gridline-color: #1c1e24;
    selection-background-color: #1e2433;
    selection-color: #60a5fa;
}

QHeaderView::section {
    background-color: #181920;
    color: #9ca3af;
    font-size: 11px;
    font-weight: 600;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #23252c;
}

QTableWidget::item {
    padding: 6px 8px;
    border-bottom: 1px solid #1a1b22;
}

QTableWidget::item:hover {
    background-color: #1a1c24;
}

QTableWidget QPushButton {
    padding: 3px 6px;
    font-size: 11px;
    font-weight: 500;
    min-height: 24px;
    max-height: 26px;
    border-radius: 4px;
}

/* ================= CHECKBOXES ================= */
QCheckBox {
    spacing: 6px;
    font-size: 12px;
    color: #d1d5db;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #374151;
    background-color: #14151a;
}

QCheckBox::indicator:hover {
    border-color: #3b82f6;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
}

/* ================= TABS ================= */
QTabWidget::pane {
    border: 1px solid #23252c;
    border-radius: 6px;
    background-color: #14151a;
    padding: 8px;
}

QTabBar::tab {
    background-color: #16171d;
    border: 1px solid #23252c;
    border-bottom: none;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
    color: #9ca3af;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 3px;
}

QTabBar::tab:selected {
    background-color: #1e2028;
    color: #60a5fa;
    border-bottom: 2px solid #3b82f6;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #1a1c22;
    color: #f3f4f6;
}

/* ================= PROJECT WORKSPACE ================= */
#project_workspace {
    background-color: #121316;
}

/* ================= SPLITTER ================= */
QSplitter::handle {
    background-color: #1a1b22;
    width: 1px;
    height: 1px;
}

/* ================= PAGINATION BAR ================= */
#pagination_bar {
    background-color: #15161d;
    border: 1px solid #23252f;
    border-radius: 8px;
}

#pagination_bar QPushButton {
    background-color: #1a1c25;
    border: 1px solid #2b2e3c;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
    color: #cbd5e1;
    min-height: 30px;
}

#pagination_bar QPushButton:hover {
    background-color: #262937;
    border-color: #3b82f6;
    color: #ffffff;
}

#pagination_bar QPushButton:disabled {
    background-color: #121318;
    border-color: #1e2029;
    color: #4b5563;
}

#pagination_bar QComboBox {
    background-color: #1a1c25;
    border: 1px solid #2b2e3c;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    color: #cbd5e1;
    min-height: 30px;
}

#pagination_bar QLabel {
    font-size: 12px;
    color: #94a3b8;
}

/* ================= 2026 PROJECT EXPERIENCE ================= */
#sidebar {
    background-color: #12151b;
    border-right: 1px solid #262c38;
    min-width: 260px;
    max-width: 260px;
}

#app_logo {
    font-size: 15px;
    font-weight: 700;
    color: #f3f5f7;
    letter-spacing: 0.8px;
}

#app_tagline, #page_subtitle, #meta_label {
    color: #70798a;
    font-size: 12px;
}

#nav_btn {
    min-height: 36px;
    margin: 2px 10px;
    padding: 0 12px;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 4px;
    background: transparent;
    color: #a7afbe;
}

#nav_btn:hover {
    background-color: #181d27;
    color: #f3f5f7;
}

#nav_btn:checked {
    background-color: #1b2130;
    border-left: 2px solid #4f7cff;
    color: #f3f5f7;
    font-weight: 600;
}

#page_heading {
    color: #f3f5f7;
    font-size: 24px;
    font-weight: 600;
}

#section_heading {
    color: #f3f5f7;
    font-size: 14px;
    font-weight: 600;
}

#dialog_title, #workspace_title, #empty_title {
    color: #f3f5f7;
    font-size: 18px;
    font-weight: 600;
}

#workspace_page, #workspace_stack {
    background-color: #0e1014;
}

#workspace_header {
    background: transparent;
    border: none;
    border-bottom: 1px solid #262c38;
}

#workspace_header #workspace_title {
    font-size: 17px;
}

#workspace_header #meta_label {
    color: #70798a;
    font-size: 11px;
}

#btn_back {
    background: transparent;
    border: none;
    color: #a7afbe;
    padding: 7px 4px;
}

#btn_back:hover {
    color: #f3f5f7;
    background: transparent;
}

#btn_icon {
    background-color: transparent;
    border: 1px solid #262c38;
    padding: 6px;
}

#project_search {
    min-height: 24px;
}

#project_table {
    background-color: #0e1014;
    alternate-background-color: #0e1014;
    border: 1px solid #262c38;
    border-radius: 6px;
    gridline-color: transparent;
    selection-background-color: #1b2130;
    selection-color: #f3f5f7;
}

#project_table QHeaderView::section {
    background-color: #12151b;
    border: none;
    border-bottom: 1px solid #262c38;
    color: #70798a;
    padding: 9px 10px;
}

#project_table::item {
    border: none;
    border-bottom: 1px solid #202631;
    padding: 8px 10px;
}

#project_table::item:hover {
    background-color: #171c26;
}

#project_action_bar {
    background-color: #12151b;
    border: none;
    border-top: 1px solid #262c38;
}

#selected_project_label {
    color: #f3f5f7;
    font-weight: 600;
}

#path_preview {
    background-color: #101319;
    border: 1px solid #262c38;
    border-radius: 6px;
}

#path_value {
    color: #a7afbe;
    font-size: 12px;
}

#field_error {
    color: #f06a6a;
    font-size: 12px;
}

QMenu {
    background-color: #151922;
    border: 1px solid #262c38;
    padding: 5px;
}

QMenu::item {
    padding: 7px 28px 7px 10px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #1b2130;
    color: #f3f5f7;
}

#project_inner_tabs::pane {
    background-color: #0e1014;
    border: none;
    border-top: 1px solid #262c38;
    padding-top: 8px;
}

#project_inner_tabs QTabBar::tab {
    min-width: 150px;
    min-height: 28px;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: #70798a;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}

#project_inner_tabs QTabBar::tab:hover {
    background-color: #151922;
    color: #a7afbe;
}

#project_inner_tabs QTabBar::tab:selected {
    background: transparent;
    border-bottom: 2px solid #4f7cff;
    color: #f3f5f7;
}
"""

def setup_theme(app: QApplication):
    """Áp dụng theme gọn gàng, tối ưu thị giác và hiệu năng."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#0e1014"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f3f5f7"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#101319"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#151922"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#151922"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#f3f5f7"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#f3f5f7"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#151922"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#f3f5f7"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4f7cff"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#4f7cff"))

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#4b5563"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#4b5563"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#4b5563"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor("#14151a"))

    app.setPalette(palette)
    app.setStyleSheet(DARK_THEME_QSS)

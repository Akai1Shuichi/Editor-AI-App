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

#central_widget, #content_container, QStackedWidget, QSplitter {
    background-color: #121316;
}

QWidget#central_widget, QWidget#content_container {
    background-color: #121316;
}

#watermark_tab, #tts_tab, #voice_lookup_tab, #settings_tab {
    background-color: #121316;
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
    min-width: 200px;
    max-width: 200px;
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
    padding: 3px 8px;
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
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #9ca3af;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e2028;
    color: #60a5fa;
    border-bottom: 2px solid #3b82f6;
}

QTabBar::tab:hover:!selected {
    background-color: #1a1c22;
    color: #f3f4f6;
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
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 12px;
    font-weight: 500;
    color: #cbd5e1;
    min-height: 26px;
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
    border-radius: 5px;
    padding: 2px 8px;
    font-size: 12px;
    color: #cbd5e1;
    min-height: 26px;
}

#pagination_bar QLabel {
    font-size: 12px;
    color: #94a3b8;
}
"""

def setup_theme(app: QApplication):
    """Áp dụng theme gọn gàng, tối ưu thị giác và hiệu năng."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#121316"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e5e7eb"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#14151a"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#181920"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#181920"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#e5e7eb"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#e5e7eb"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1e2029"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#e5e7eb"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#2563eb"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#3b82f6"))

    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor("#4b5563"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#4b5563"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#4b5563"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button, QColor("#14151a"))

    app.setPalette(palette)
    app.setStyleSheet(DARK_THEME_QSS)

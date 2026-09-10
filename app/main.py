import sys
import os

# Thêm đường dẫn thư mục gốc editor video app vào sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from app.styles import setup_theme
from app.ui.main_window import MainWindow

def main():
    # Bật tính năng High DPI Scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Media Studio")
    app.setOrganizationName("AI Studio")

    # Áp dụng Fusion Style và Dark Palette toàn cục để loại bỏ hoàn toàn nhấp nháy/vết trắng
    setup_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

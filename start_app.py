#!/usr/bin/env python3
"""
Entry point để khởi chạy ứng dụng AI Media Studio (PyQt6 Modern Dark Theme).
Chạy:
    python3 start_app.py
Hoặc kích hoạt virtualenv:
    source .venv/bin/activate && python3 start_app.py
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ưu tiên sử dụng python trong virtualenv nếu đang chạy từ python ngoài
venv_python = (BASE_DIR / ".venv" / "Scripts" / "python.exe") if sys.platform == "win32" else (BASE_DIR / ".venv" / "bin" / "python")
if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
    import subprocess
    sys.exit(subprocess.call([str(venv_python)] + sys.argv))

from app.main import main

if __name__ == "__main__":
    main()

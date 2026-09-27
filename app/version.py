"""Read the packaged application version without making network requests."""

import json
import sys
from pathlib import Path


def _version_file() -> Path:
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        return root / "app" / "data" / "config" / "version.json"
    return Path(__file__).parent / "data" / "config" / "version.json"


def load_app_version() -> str:
    try:
        return str(json.loads(_version_file().read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError, TypeError):
        return "1.1"


APP_VERSION = load_app_version()

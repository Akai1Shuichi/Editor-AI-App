"""Persistent state for tools that live directly in the main sidebar."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from PyQt6.QtCore import QSettings


def build_output_folder_name(
    prefix: str,
    instant: Optional[datetime] = None,
    *,
    day_first: bool = False,
) -> str:
    """Return a readable, sortable name for one standalone export run."""
    current = instant or datetime.now()
    date_format = "%d%m%Y" if day_first else "%Y%m%d"
    return f"{prefix}_{current.strftime(date_format)}_{current.strftime('%H%M%S')}"


def resolve_new_output_folder(root: Path, name: str) -> Path:
    """Resolve a direct child output folder without allowing overwrites."""
    clean_name = name.strip()
    if not clean_name or clean_name in {".", ".."}:
        raise ValueError("Tên thư mục không được để trống.")
    invalid_chars = '<>:"/\\|?*'
    reserved_names = {"CON", "PRN", "AUX", "NUL"}
    reserved_names.update(f"COM{index}" for index in range(1, 10))
    reserved_names.update(f"LPT{index}" for index in range(1, 10))
    if (
        Path(clean_name).name != clean_name
        or any(char in clean_name for char in invalid_chars)
        or any(ord(char) < 32 for char in clean_name)
        or clean_name.endswith((".", " "))
        or Path(clean_name).stem.upper() in reserved_names
    ):
        raise ValueError("Tên thư mục chứa ký tự không hợp lệ.")

    output_folder = Path(root) / clean_name
    if output_folder.exists():
        raise FileExistsError(f"Thư mục '{clean_name}' đã tồn tại.")
    return output_folder


class StandaloneStateStore:
    """Keep sidebar-tool state separate from project metadata."""

    WATERMARK_KEY = "standalone/watermark"
    TTS_KEY = "standalone/tts"
    LAST_PAGE_KEY = "window/last_sidebar_page"
    VALID_PAGES = range(4)

    def __init__(self, settings: Optional[QSettings] = None):
        self.settings = settings or QSettings()

    def save_last_page(self, index: int) -> None:
        self.settings.setValue(self.LAST_PAGE_KEY, int(index))
        self.settings.sync()

    def load_last_page(self) -> int:
        try:
            index = int(self.settings.value(self.LAST_PAGE_KEY, 0))
        except (TypeError, ValueError):
            return 0
        return index if index in self.VALID_PAGES else 0

    def save_watermark(
        self, files: Iterable[Path], output_dir: Optional[Path]
    ) -> None:
        payload = {
            "files": [str(Path(path)) for path in files],
            "output_dir": str(output_dir) if output_dir else "",
        }
        self._save_json(self.WATERMARK_KEY, payload)

    def load_watermark(self) -> Dict[str, Any]:
        payload = self._load_json(self.WATERMARK_KEY)
        files = [
            Path(value)
            for value in payload.get("files", [])
            if value and Path(value).is_file()
        ]
        output_value = payload.get("output_dir", "")
        output_dir = Path(output_value) if output_value else None
        if output_dir and not output_dir.is_dir():
            output_dir = None
        return {"files": files, "output_dir": output_dir}

    def save_tts(self, state: Dict[str, Any]) -> None:
        self._save_json(self.TTS_KEY, state)

    def load_tts(self) -> Dict[str, Any]:
        payload = self._load_json(self.TTS_KEY)
        for key in ("audio_path", "srt_path"):
            value = payload.get(key)
            payload[key] = Path(value) if value and Path(value).is_file() else None
        output_value = payload.get("output_dir")
        payload["output_dir"] = (
            Path(output_value) if output_value and Path(output_value).is_dir() else None
        )
        return payload

    def _save_json(self, key: str, payload: Dict[str, Any]) -> None:
        self.settings.setValue(
            key,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        )
        self.settings.sync()

    def _load_json(self, key: str) -> Dict[str, Any]:
        raw = self.settings.value(key, "")
        if not raw:
            return {}
        try:
            value = json.loads(str(raw))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return value if isinstance(value, dict) else {}

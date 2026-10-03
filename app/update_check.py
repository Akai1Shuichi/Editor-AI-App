"""Check the release API for a newer application version."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import certifi
import requests
from PyQt6.QtCore import QThread, pyqtSignal

from app.version import APP_VERSION, _version_file
from app.update_install import download_and_stage


def is_newer_version(latest: str, current: str) -> bool:
    def parts(value: str) -> tuple[int, ...]:
        numbers = []
        for part in value.strip().lstrip("vV").split("."):
            digits = ""
            for char in part:
                if not char.isdigit():
                    break
                digits += char
            if digits:
                numbers.append(int(digits))
        while len(numbers) > 1 and numbers[-1] == 0:
            numbers.pop()
        return tuple(numbers) or (0,)

    return parts(latest) > parts(current)


def parse_update_response(response: dict[str, Any], *, current_version: str) -> dict[str, Any] | None:
    if not response.get("success"):
        raise ValueError(str(response.get("message") or "Máy chủ không thể kiểm tra bản cập nhật."))
    data = response.get("data")
    if not isinstance(data, dict):
        raise ValueError("Phản hồi kiểm tra cập nhật không hợp lệ.")
    version = str(data.get("latestVersion") or "")
    if not data.get("hasNewVersion") or not version or not is_newer_version(version, current_version):
        return None
    return {
        "version": version,
        "notes": str(data.get("changeLog") or data.get("message") or "Không có nhật ký thay đổi."),
        "download_links": data.get("downloadLink") if isinstance(data.get("downloadLink"), list) else [],
    }


class UpdateCheckerThread(QThread):
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    check_failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            settings = json.loads(_version_file().read_text(encoding="utf-8"))
            api_base = str(settings["api_base_url"]).rstrip("/")
            software_code = str(settings["software_code"])
            response = requests.post(
                f"{api_base}/update/check",
                json={"code": software_code, "currentVersion": APP_VERSION},
                headers={"User-Agent": "EditorVideoAI-Updater"},
                timeout=8,
                verify=certifi.where(),
            )
            response.raise_for_status()
            update = parse_update_response(response.json(), current_version=APP_VERSION)
            if update is None:
                self.no_update.emit()
            else:
                self.update_available.emit(update)
        except (OSError, KeyError, TypeError, ValueError, requests.RequestException) as error:
            self.check_failed.emit(str(error))


class UpdateDownloadThread(QThread):
    progress = pyqtSignal(int)
    staged = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, url: str, target: Path, parent=None):
        super().__init__(parent)
        self.url = url
        self.target = target

    def run(self) -> None:
        try:
            staged = download_and_stage(self.url, self.target, self.progress.emit)
            self.staged.emit(str(staged))
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, requests.RequestException) as error:
            self.failed.emit(str(error))

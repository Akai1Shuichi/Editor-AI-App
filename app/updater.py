"""Kiểm tra và tải bản phát hành mới từ API của S Editor."""

from __future__ import annotations

import json
import platform
import sys
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.update_download import update_package_filename


DEFAULT_CONFIG = {
    "version": "1.1",
    "api_base_url": "http://localhost:3000/api/v1",
    "software_code": "s-editor",
    "telemetry_debug": False,
}


def _config_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "app" / "data" / "config" / "version.json"
    return Path(__file__).parent / "data" / "config" / "version.json"


def load_config() -> dict[str, Any]:
    try:
        return {**DEFAULT_CONFIG, **json.loads(_config_path().read_text(encoding="utf-8"))}
    except (OSError, ValueError, TypeError):
        return dict(DEFAULT_CONFIG)


def load_app_version() -> str:
    return str(load_config()["version"])


def load_api_base_url() -> str:
    return str(load_config()["api_base_url"]).rstrip("/")


def load_software_code() -> str:
    return str(load_config()["software_code"])


def load_telemetry_debug() -> bool:
    return bool(load_config().get("telemetry_debug", False))


APP_VERSION = load_app_version()
DEFAULT_API_BASE_URL = load_api_base_url()
DEFAULT_SOFTWARE_CODE = load_software_code()


def update_download_directory() -> Path:
    """Keep the release package beside the packaged app."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def parse_version(value: str) -> tuple[int, ...]:
    """Chuẩn hoá ``v1.2.3-beta`` để so sánh phiên bản phát hành."""
    parts: list[int] = []
    for part in value.lstrip("vV").strip().split("."):
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        if digits:
            parts.append(int(digits))
    return tuple(parts) or (0,)


def is_newer_version(latest_tag: str, current_version: str | None = None) -> bool:
    return parse_version(latest_tag) > parse_version(current_version or load_app_version())


def current_os() -> tuple[str, str]:
    system = platform.system().lower()
    return {
        "windows": ("windows", "Windows"),
        "darwin": ("macos", "macOS"),
        "linux": ("linux", "Linux"),
    }.get(system, (system or "linux", platform.system()))


def build_update_check_request(api_base_url: str, software_code: str, current_version: str) -> urllib.request.Request:
    body = json.dumps({"code": software_code, "currentVersion": current_version}).encode("utf-8")
    return urllib.request.Request(
        f"{api_base_url.rstrip('/')}/update/check",
        data=body,
        headers={"User-Agent": "EditorVideoAI-Updater", "Content-Type": "application/json"},
        method="POST",
    )


def build_update_download_url(api_base_url: str, software_code: str, version: str) -> str:
    os_name, _ = current_os()
    query = urlencode({"code": software_code, "versionName": version, "os": os_name})
    return f"{api_base_url.rstrip('/')}/update/download?{query}"


def parse_update_response(response: dict[str, Any], *, current_version: str) -> dict[str, Any] | None:
    if not response.get("success"):
        raise ValueError(str(response.get("message") or "Máy chủ không thể kiểm tra bản cập nhật."))
    data = response.get("data")
    if not isinstance(data, dict):
        raise ValueError("Phản hồi kiểm tra cập nhật không hợp lệ.")
    if not data.get("hasNewVersion"):
        return None
    version = str(data.get("latestVersion") or "")
    if not version or not is_newer_version(version, current_version):
        return None
    _, os_display = current_os()
    return {
        "version": version,
        "current_version": current_version,
        "notes": str(data.get("changeLog") or data.get("message") or "Không có nhật ký thay đổi."),
        "message": str(data.get("message") or "Đã có bản cập nhật mới."),
        "os_name": os_display,
    }


class UpdateCheckerThread(QThread):
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal(str)
    check_failed = pyqtSignal(str)

    def __init__(self, parent=None, *, api_base_url: str | None = None, software_code: str | None = None, current_version: str | None = None):
        super().__init__(parent)
        self.api_base_url = api_base_url or load_api_base_url()
        self.software_code = software_code or load_software_code()
        self.current_version = current_version or load_app_version()

    def run(self) -> None:
        from app.core.telemetry import api_request

        partial: Path | None = None
        try:
            request = build_update_check_request(self.api_base_url, self.software_code, self.current_version)
            response = api_request(
                "POST",
                request.full_url,
                json=json.loads(request.data),
                headers={"User-Agent": "EditorVideoAI-Updater"},
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            update_info = parse_update_response(payload, current_version=self.current_version)
            if update_info is None:
                self.no_update.emit(f"Bạn đang sử dụng phiên bản mới nhất ({self.current_version}).")
                return
            update_info["download_url"] = build_update_download_url(
                self.api_base_url, self.software_code, update_info["version"]
            )
            self.update_available.emit(update_info)
        except requests.HTTPError as error:
            code = error.response.status_code
            self.check_failed.emit("Chưa tìm thấy bản cập nhật." if code == 404 else f"Máy chủ cập nhật trả về lỗi HTTP {code}.")
        except (requests.RequestException, ValueError) as error:
            self.check_failed.emit(f"Không thể kiểm tra bản cập nhật: {error}")


class UpdateDownloaderThread(QThread):
    progress = pyqtSignal(int, int, float)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, download_url: str, file_name: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.file_name = Path(file_name).name or "EditorVideoAI-update.zip"
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        from app.core.telemetry import api_request

        try:
            destination = update_download_directory()
            with api_request(
                "GET",
                self.download_url,
                headers={"User-Agent": "EditorVideoAI-Updater"},
                stream=True,
                timeout=30,
            ) as response:
                response.raise_for_status()
                downloaded_name = update_package_filename(
                    response.url, response.headers.get("Content-Disposition"), self.file_name
                )
                target = destination / downloaded_name
                partial = target.with_name(target.name + ".part")
                with partial.open("wb") as stream:
                    total = int(response.headers.get("Content-Length", 0))
                    received = 0
                    for chunk in response.iter_content(chunk_size=65536):
                        if not chunk:
                            continue
                        if self._cancelled:
                            partial.unlink(missing_ok=True)
                            self.failed.emit("Đã hủy tải bản cập nhật.")
                            return
                        stream.write(chunk)
                        received += len(chunk)
                        self.progress.emit(received, total, received * 100 / total if total else 0)
                partial.replace(target)
            self.finished.emit(str(target))
        except (OSError, requests.RequestException) as error:
            if partial is not None:
                partial.unlink(missing_ok=True)
            self.failed.emit(f"Không thể tải bản cập nhật: {error}")


class UpdateDialog(QDialog):
    def __init__(self, update_info: dict[str, Any], parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.downloader: UpdateDownloaderThread | None = None
        self.setWindowTitle("Bản cập nhật mới — Editor Video AI")
        self.setMinimumSize(520, 390)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        title = QLabel(f"Đã có bản cập nhật mới: <b>{self.update_info['version']}</b>")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #22c55e;")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"Phiên bản hiện tại: {self.update_info['current_version']}  •  {self.update_info['os_name']}"))
        notes = QTextEdit()
        notes.setHtml(self.update_info.get("notes", "Không có mô tả."))
        notes.setReadOnly(True)
        layout.addWidget(notes, 1)
        layout.addWidget(QLabel("Gói cập nhật sẽ được lưu cạnh ứng dụng để bạn tự cài đặt."))
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.cancel_button = QPushButton("Để sau")
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)
        self.download_button = QPushButton("Tải cập nhật")
        self.download_button.setEnabled(bool(self.update_info.get("download_url")))
        self.download_button.clicked.connect(self._start_download)
        buttons.addWidget(self.download_button)
        layout.addLayout(buttons)

    def _start_download(self) -> None:
        self.download_button.setEnabled(False)
        self.cancel_button.setText("Hủy tải")
        self.progress.setVisible(True)
        self.downloader = UpdateDownloaderThread(self.update_info["download_url"], "", self)
        self.downloader.progress.connect(self._update_progress)
        self.downloader.finished.connect(self._download_finished)
        self.downloader.failed.connect(self._download_failed)
        self.downloader.start()

    @pyqtSlot(int, int, float)
    def _update_progress(self, received: int, total: int, percent: float) -> None:
        self.progress.setValue(int(percent))
        self.progress.setFormat(f"Đang tải {percent:.1f}% ({received / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB)")

    @pyqtSlot(str)
    def _download_finished(self, archive: str) -> None:
        QMessageBox.information(
            self,
            "Đã tải bản cập nhật",
            f"Đã lưu gói cập nhật tại:\n{archive}\n\nỨng dụng sẽ đóng. Hãy giải nén ZIP và chạy ứng dụng trong thư mục đã giải nén.",
        )
        self.cancel_button.setEnabled(False)
        self.accept()
        application = QApplication.instance()
        if application:
            application.quit()

    @pyqtSlot(str)
    def _download_failed(self, message: str) -> None:
        self.progress.setVisible(False)
        self.download_button.setEnabled(True)
        self.cancel_button.setText("Để sau")
        QMessageBox.warning(self, "Không thể tải cập nhật", message)

    def reject(self) -> None:
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()
            self.downloader.wait()
        super().reject()

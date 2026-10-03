"""Stage a release beside the installed executable and replace it after exit."""

from __future__ import annotations

import ctypes
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlsplit

import certifi
import requests


MAX_DOWNLOAD_BYTES = 2 * 1024 * 1024 * 1024


def select_download_url(links: Iterable[str], platform: str | None = None) -> str | None:
    """Pick this OS's HTTPS package from the API's downloadLink list."""
    names = {"win32": "Windows", "darwin": "macOS", "linux": "Linux"}
    platform_name = names.get(platform or sys.platform)
    if not platform_name:
        return None
    suffix = f"-{platform_name.lower()}.zip"
    for link in links:
        if not isinstance(link, str):
            continue
        try:
            parsed = urlsplit(link)
            if (parsed.scheme.lower() == "https" and parsed.hostname
                    and not parsed.username and not parsed.password
                    and parsed.path.lower().endswith(suffix)):
                return link
        except ValueError:
            continue
    return None


def download_and_stage(url: str, target: Path,
                       progress: Callable[[int], None] | None = None) -> Path:
    """Download a release ZIP and stage only its executable on the target volume."""
    target = Path(target)
    if not target.is_file():
        raise ValueError("Không tìm thấy file ứng dụng đã cài.")
    if target.name not in ("EditorVideoApp.exe", "EditorVideoApp"):
        raise ValueError("Không thể tự cập nhật file ứng dụng này.")
    stage_dir = Path(tempfile.mkdtemp(prefix=".editor-update-", dir=target.parent))
    archive_path = stage_dir / "release.zip"
    staged = stage_dir / target.name
    try:
        response = requests.get(
            url, stream=True, timeout=(10, 30), verify=certifi.where(),
            headers={"User-Agent": "EditorVideoAI-Updater"},
        )
        try:
            response.raise_for_status()
            length = int(response.headers.get("Content-Length") or 0)
            if length > MAX_DOWNLOAD_BYTES:
                raise ValueError("Gói cập nhật quá lớn.")
            received = 0
            with archive_path.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > MAX_DOWNLOAD_BYTES:
                        raise ValueError("Gói cập nhật quá lớn.")
                    output.write(chunk)
                    if progress and length:
                        progress(min(100, received * 100 // length))
            if length and received != length:
                raise ValueError("Gói cập nhật tải chưa đầy đủ.")
        finally:
            response.close()
        with zipfile.ZipFile(archive_path) as archive:
            info = archive.getinfo(target.name)
            if not 0 < info.file_size <= MAX_DOWNLOAD_BYTES:
                raise ValueError("File ứng dụng trong gói cập nhật không hợp lệ.")
            with archive.open(info) as source, staged.open("wb") as output:
                shutil.copyfileobj(source, output)
        if os.name != "nt":
            staged.chmod(0o755)
        archive_path.unlink()
        return staged
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise


def apply_staged_update(target: Path, staged: Path) -> None:
    """Atomically replace the installed executable after it exits."""
    target, staged = Path(target), Path(staged)
    if not target.is_file() or not staged.is_file():
        raise FileNotFoundError("Thiếu file ứng dụng cũ hoặc bản cập nhật.")
    # PyInstaller's one-file parent may hold the executable briefly after
    # the GUI process exits while it cleans up its extraction directory.
    deadline = time.monotonic() + 120
    while True:
        try:
            os.replace(staged, target)
            return
        except PermissionError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.5)


def _wait_for_parent(pid: int, timeout_seconds: int = 120) -> None:
    if sys.platform == "win32":
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.CloseHandle.restype = ctypes.c_int
        handle = kernel.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, timeout_seconds * 1000) != 0:
                    raise TimeoutError("Ứng dụng cũ chưa đóng.")
            finally:
                kernel.CloseHandle(handle)
        return
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.2)
    raise TimeoutError("Ứng dụng cũ chưa đóng.")


def launch_update_helper(target: Path, staged: Path) -> None:
    """Run a temporary copy of the packaged app after its original exits."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Tự cập nhật chỉ hỗ trợ bản ứng dụng đã đóng gói.")
    target = Path(target).resolve()
    staged = Path(staged).resolve()
    if staged.parent.parent != target.parent:
        raise ValueError("File cập nhật không nằm cạnh ứng dụng hiện tại.")
    helper_key = hashlib.sha256(str(target).encode("utf-8")).hexdigest()[:16]
    helper_dir = Path(tempfile.gettempdir()) / f"EditorVideoAI-updater-{helper_key}"
    helper_dir.mkdir(parents=True, exist_ok=True)
    helper = helper_dir / target.name
    shutil.copy2(sys.executable, helper)
    if os.name != "nt":
        helper.chmod(0o755)
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(
        [str(helper), "--apply-update", str(target), str(staged), str(os.getpid())],
        cwd=str(target.parent), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        close_fds=True, creationflags=flags,
        env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"},
    )


def run_update_helper(target: Path, staged: Path, parent_pid: int) -> int:
    """Entry point of the temporary helper executable."""
    target, staged = Path(target), Path(staged)
    marker = target.parent / ".editor-update-error.txt"
    try:
        _wait_for_parent(parent_pid)
        apply_staged_update(target, staged)
        shutil.rmtree(staged.parent, ignore_errors=True)
        marker.unlink(missing_ok=True)
        flags = 0
        if sys.platform == "win32":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            [str(target)], cwd=str(target.parent), stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            close_fds=True, creationflags=flags,
            env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"},
        )
        return 0
    except Exception as error:
        try:
            marker.write_text(str(error), encoding="utf-8")
        except OSError:
            pass
        return 1

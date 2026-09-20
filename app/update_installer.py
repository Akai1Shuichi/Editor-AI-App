"""Install a downloaded packaged release after the running app has exited."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def supports_in_place_update() -> bool:
    """Only a packaged executable may replace its own installation."""
    return bool(getattr(sys, "frozen", False))


def installation_directory() -> Path:
    return Path(sys.executable).resolve().parent


def _helper_directory() -> Path:
    directory = Path(tempfile.gettempdir()) / "EditorVideoAI-Updates"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _shell_script(staging: Path, install: Path, executable_name: str) -> str:
    staged = shlex.quote(str(staging))
    destination = shlex.quote(str(install))
    executable = shlex.quote(executable_name)
    return f"""#!/bin/sh
set -eu
parent_pid="$1"
staging={staged}
install={destination}
executable={executable}
target="$install/$executable"
backup="$install/.editor-video-ai-update-backup-$$"

while kill -0 "$parent_pid" 2>/dev/null; do sleep 1; done

restore() {{
    if [ -d "$backup" ]; then
        if [ -e "$backup/$executable" ]; then
            rm -f "$target"
            mv "$backup/$executable" "$target"
        fi
        rmdir "$backup" 2>/dev/null || true
    fi
}}

if [ -e "$target" ]; then
    mkdir "$backup"
    mv "$target" "$backup/$executable"
fi

if ! cp -a "$staging/." "$install/"; then
    restore
    exit 1
fi

if [ ! -x "$target" ]; then chmod +x "$target"; fi
"$target" >/dev/null 2>&1 &

rm -rf "$backup" "$staging"
rm -f "$0"
"""


def _powershell_script(staging: Path, install: Path, executable_name: str) -> str:
    def quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    staged = quote(str(staging))
    destination = quote(str(install))
    executable = quote(executable_name)
    return f"""param([int]$ParentPid)
$ErrorActionPreference = 'Stop'
$staging = {staged}
$install = {destination}
$executable = {executable}
$target = Join-Path $install $executable
$backup = Join-Path $install ('.editor-video-ai-update-backup-' + $PID)

while (Get-Process -Id $ParentPid -ErrorAction SilentlyContinue) {{ Start-Sleep -Seconds 1 }}
try {{
    if (Test-Path $target) {{
        New-Item -ItemType Directory -Path $backup | Out-Null
        Move-Item -LiteralPath $target -Destination (Join-Path $backup $executable) -Force
    }}
    Copy-Item -Path (Join-Path $staging '*') -Destination $install -Recurse -Force
    Start-Process -FilePath $target
    Remove-Item -LiteralPath $backup -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
    if (Test-Path (Join-Path $backup $executable)) {{
        Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
        Move-Item -LiteralPath (Join-Path $backup $executable) -Destination $target -Force
    }}
    $_ | Out-File -FilePath (Join-Path $env:TEMP 'EditorVideoAI-Updates\\install-error.log') -Append
    exit 1
}}
"""


def create_update_helper(
    staging_directory: Path,
    install_directory: Path,
    executable_name: str,
    *,
    platform_name: str | None = None,
) -> Path:
    """Write a detached helper that swaps the app after its parent exits."""
    staging = Path(staging_directory).resolve()
    install = Path(install_directory).resolve()
    name = Path(executable_name).name
    if not staging.is_dir() or not name or name in {".", ".."}:
        raise ValueError("Thư mục cập nhật hoặc tên ứng dụng không hợp lệ.")

    platform_name = platform_name or sys.platform
    helper = _helper_directory() / f"install-{uuid.uuid4().hex}"
    if platform_name == "win32":
        helper = helper.with_suffix(".ps1")
        helper.write_text(_powershell_script(staging, install, name), encoding="utf-8")
    else:
        helper = helper.with_suffix(".sh")
        helper.write_text(_shell_script(staging, install, name), encoding="utf-8")
        helper.chmod(0o700)
    return helper


def helper_command(helper: Path, parent_pid: int, *, platform_name: str | None = None) -> list[str]:
    platform_name = platform_name or sys.platform
    if platform_name == "win32":
        return ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper), str(parent_pid)]
    return ["/bin/sh", str(helper), str(parent_pid)]


def start_update_handoff(staging_directory: Path, executable_name: str | None = None) -> Path:
    """Start the replacement helper, then let the caller terminate this app."""
    if not supports_in_place_update():
        raise OSError("Chỉ bản ứng dụng đã đóng gói mới có thể tự cài đặt cập nhật.")

    staging = Path(staging_directory).resolve()
    install = installation_directory()
    name = Path(executable_name or sys.executable).name
    if not (staging / name).is_file():
        raise OSError("Gói cập nhật không chứa tệp chạy của ứng dụng.")

    helper = create_update_helper(staging, install, name)
    kwargs: dict[str, object] = {"close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(helper_command(helper, os.getpid()), **kwargs)
    return helper

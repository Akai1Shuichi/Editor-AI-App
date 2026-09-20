"""Names downloaded update packages safely after redirects."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse


def _content_disposition_filename(header: str | None) -> str:
    if not header:
        return ""
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^;\"]+)", header, flags=re.IGNORECASE)
    return unquote(match.group(1).strip()) if match else ""


def update_package_filename(response_url: str, content_disposition: str | None, fallback: str) -> str:
    """Return a ZIP filename even when an API redirect ends at `/download`."""
    candidates = (
        _content_disposition_filename(content_disposition),
        Path(unquote(urlparse(response_url).path)).name,
        Path(fallback).name,
    )
    for candidate in candidates:
        if Path(candidate).suffix.lower() == ".zip":
            return Path(candidate).name
    return Path(fallback).with_suffix(".zip").name

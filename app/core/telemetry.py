"""Best-effort lifecycle telemetry for the S Editor backend."""

from __future__ import annotations

import hashlib
import logging
import platform
from typing import Optional
from urllib.parse import quote
import uuid

import requests
from PyQt6.QtCore import QThread

from app.updater import load_api_base_url, load_app_version


WATERMARK_TYPE = "WATERMARK_GGFLOW"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def safe_device_id(current_device_id: str) -> str:
    """Return a masked device identifier suitable for diagnostic logs."""
    if not current_device_id:
        return "<empty>"
    return f"{current_device_id[:4]}...{current_device_id[-4:]}"


def api_request(method: str, url: str, *, session: Optional[requests.Session] = None, **kwargs):
    """Make a telemetry request while logging a privacy-safe request trace."""
    logger.debug("REQUEST %s %s", method.upper(), url)
    payload = kwargs.get("json")
    if isinstance(payload, dict):
        payload = payload.copy()
        if "device_id" in payload:
            payload["device_id"] = safe_device_id(str(payload["device_id"]))
        logger.debug("REQUEST BODY: %s", payload)

    try:
        requester = session.request if session is not None else requests.request
        response = requester(method, url, **kwargs)
        logger.debug("RESPONSE %s %s", response.status_code, response.text)
        return response
    except requests.RequestException:
        logger.exception("NETWORK ERROR %s %s", method.upper(), url)
        raise


def device_id() -> str:
    """Return a stable, one-way identifier without sending the raw machine values."""
    raw_identifier = f"{platform.node()}:{uuid.getnode()}"
    return hashlib.sha256(raw_identifier.encode("utf-8")).hexdigest()


def should_record_watermark(*, success_count: int, cancelled: bool) -> bool:
    return success_count > 0 and not cancelled


class TelemetryClient:
    """Small client for unauthenticated installation and watermark events."""

    def __init__(self, api_base_url: str, *, session: Optional[requests.Session] = None):
        self.api_base_url = api_base_url.rstrip("/")
        self.session = session or requests.Session()

    def ensure_installation(self, current_device_id: str, version: str) -> bool:
        try:
            response = api_request(
                "GET",
                f"{self.api_base_url}/installations/check/{quote(current_device_id, safe='')}",
                session=self.session,
                timeout=5,
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("success") and payload.get("data", {}).get("installed"):
                return False

            response = api_request(
                "POST",
                f"{self.api_base_url}/installations",
                session=self.session,
                json={"device_id": current_device_id, "version": version},
                timeout=5,
            )
            response.raise_for_status()
            return bool(response.json().get("success"))
        except (requests.RequestException, ValueError, AttributeError):
            return False

    def record_watermark(self, current_device_id: str) -> bool:
        try:
            response = api_request(
                "POST",
                f"{self.api_base_url}/watermarks",
                session=self.session,
                json={"device_id": current_device_id, "type": WATERMARK_TYPE},
                timeout=5,
            )
            response.raise_for_status()
            return bool(response.json().get("success"))
        except (requests.RequestException, ValueError, AttributeError):
            return False


class TelemetryThread(QThread):
    """Runs non-critical telemetry away from the Qt UI thread."""

    def __init__(self, event: str, parent=None):
        super().__init__(parent)
        self.event = event

    def run(self) -> None:
        client = TelemetryClient(load_api_base_url())
        current_device_id = device_id()
        if self.event == "installation":
            client.ensure_installation(current_device_id, load_app_version())
        elif self.event == "watermark":
            client.record_watermark(current_device_id)

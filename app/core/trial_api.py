"""Public API client for checking whether a feature trial is available."""

from __future__ import annotations

from urllib.parse import urlencode

from app.core.telemetry import api_request
from app.updater import load_api_base_url


VIDEO_WATERMARK_TYPE = "WATERMARK_VIDEO"


class TrialClient:
    def __init__(self, api_base_url: str | None = None):
        self.api_base_url = (api_base_url or load_api_base_url()).rstrip("/")

    def get_trial(self, trial_type: str) -> dict:
        """GET /trials/check?type=<type> and return its data object."""
        response = api_request(
            "GET",
            f"{self.api_base_url}/trials/check?{urlencode({'type': trial_type})}",
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise ValueError("Không thể kiểm tra quyền dùng thử")
        data = payload.get("data")
        if not isinstance(data, dict) or type(data.get("isTrial")) is not bool:
            raise ValueError("Phản hồi dùng thử không hợp lệ")
        return data

    def check(self, trial_type: str) -> bool:
        payload = self.get_trial(trial_type)
        if type(payload.get("isTrial")) is not bool:
            raise ValueError("Phản hồi dùng thử không hợp lệ")
        return payload["isTrial"]

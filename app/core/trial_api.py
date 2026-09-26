"""Temporary public trial-check response until the backend endpoint is ready."""

from __future__ import annotations

from urllib.parse import quote

import requests

from app.updater import load_api_base_url


VIDEO_WATERMARK_TYPE = "WATERMARK_VIDEO"

# Change this response to {"isTrial": False} to preview the blocked state.
MOCK_TRIAL_RESPONSES = {
    VIDEO_WATERMARK_TYPE: {"isTrial": True},
}


class TrialClient:
    def __init__(self, api_base_url: str | None = None, *, use_mock: bool = True):
        self.api_base_url = (api_base_url or load_api_base_url()).rstrip("/")
        self.use_mock = use_mock

    def get_trial(self, trial_type: str) -> dict:
        """GET public trial state by type; use mock data until the API exists."""
        if self.use_mock:
            response = MOCK_TRIAL_RESPONSES.get(trial_type)
            if response is None:
                raise ValueError(f"Loại tính năng không hợp lệ: {trial_type}")
            return response.copy()

        response = requests.get(
            f"{self.api_base_url}/trials/{quote(trial_type, safe='')}", timeout=5
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and "data" in payload:
            payload = payload["data"]
        if not isinstance(payload, dict) or type(payload.get("isTrial")) is not bool:
            raise ValueError("Phản hồi dùng thử không hợp lệ")
        return payload

    def check(self, trial_type: str) -> bool:
        payload = self.get_trial(trial_type)
        if type(payload.get("isTrial")) is not bool:
            raise ValueError("Phản hồi dùng thử không hợp lệ")
        return payload["isTrial"]

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable
import requests

from app import config
from app.core.telemetry import api_request

class VibiAPIError(Exception):
    """Lỗi phát sinh khi gọi Vibi API."""
    pass

class VibiClient:
    """Client tương tác với Vibi API (https://api.vibi.pro) cho ElevenLabs TTS."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or config.VIBI_API_KEY
        self.base_url = (base_url or config.VIBI_API_BASE or "https://api.vibi.pro").rstrip("/")
        self.session = requests.Session()

    def set_api_key(self, key: str):
        """Cập nhật API key cho client."""
        self.api_key = key.strip()

    def is_configured(self) -> bool:
        """Kiểm tra xem API key đã được cấu hình chưa."""
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    def _request(self, method: str, url: str, **kwargs):
        return api_request(
            method, url, session=self.session, log_body=False, log_response=False, **kwargs
        )

    def _get_headers(self) -> Dict[str, str]:
        """Tạo headers chứa authentication xi-api-key."""
        if not self.is_configured():
            raise VibiAPIError("Voice API Key chưa được cài đặt! Vui lòng nhập và lưu API Key trước khi sử dụng.")
        return {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "PyQt6-VoiceAPIClient/1.0"
        }

    def get_account_info(self) -> Dict[str, Any]:
        """Lấy thông tin tài khoản và số dư credits (GET /v1/auth/me)."""
        url = f"{self.base_url}/v1/auth/me"
        try:
            res = self._request("GET", url, headers=self._get_headers(), timeout=15)
            if res.status_code == 401:
                raise VibiAPIError("API Key Voice API không chính xác hoặc đã hết hạn (Mã lỗi 401)!")
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
                raise VibiAPIError("API Key Voice API không chính xác hoặc đã hết hạn (Mã lỗi 401)!")
            raise VibiAPIError(f"Không thể kết nối đến Voice API: {e}")

    def get_models(self, provider: str = "elevenlabs") -> List[Dict[str, Any]]:
        """Lấy danh sách các model khả dụng (GET /v1/models)."""
        url = f"{self.base_url}/v1/models"
        params = {"provider": provider}
        try:
            res = self._request("GET", url, headers=self._get_headers(), params=params, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi lấy danh sách model: {e}")

    def list_default_voices(self, search: Optional[str] = None, page_size: int = 50) -> List[Dict[str, Any]]:
        """Liệt kê các giọng premade/mặc định của ElevenLabs (GET /v1/default-voices)."""
        url = f"{self.base_url}/v1/default-voices"
        params: Dict[str, Any] = {"page_size": page_size}
        if search:
            params["search"] = search
        try:
            res = self._request("GET", url, headers=self._get_headers(), params=params, timeout=15)
            res.raise_for_status()
            data = res.json()
            return data.get("voices", [])
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi lấy danh sách giọng mặc định: {e}")

    def list_shared_voices(
        self,
        search: Optional[str] = None,
        page_size: int = 30,
        page: int = 0,
        sort: str = "trending",
        gender: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tìm kiếm thư viện giọng ElevenLabs dùng chung (GET /v1/shared-voices)."""
        url = f"{self.base_url}/v1/shared-voices"
        params: Dict[str, Any] = {
            "page_size": page_size,
            "page": page,
            "sort": sort,
        }
        if search:
            params["search"] = search
        if gender and gender.lower() != "all":
            params["gender"] = gender
        if language and language.lower() != "all":
            params["required_languages"] = language

        try:
            res = self._request("GET", url, headers=self._get_headers(), params=params, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi tra cứu thư viện giọng shared: {e}")

    def list_minimax_system_voices(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 30,
        gender: Optional[str] = None,
        language: Optional[str] = None,
        accent: Optional[str] = None,
        age: Optional[str] = None,
        use_cases: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tìm kiếm thư viện giọng hệ thống MiniMax (GET /v1/minimax/system-voices)."""
        url = f"{self.base_url}/v1/minimax/system-voices"
        params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if search:
            params["search"] = search
        if gender and gender.lower() != "all":
            params["gender"] = gender.capitalize()
        if language and language.lower() != "all":
            params["language"] = language
        if accent and accent.lower() != "all":
            params["accent"] = accent
        if age and age.lower() != "all":
            params["age"] = age
        if use_cases and use_cases.lower() != "all":
            params["use_cases"] = use_cases

        try:
            res = self._request("GET", url, headers=self._get_headers(), params=params, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi tra cứu giọng MiniMax: {e}")

    def list_minimax_cloned_voices(self) -> List[Dict[str, Any]]:
        """Lấy danh sách các giọng MiniMax đã clone của người dùng (GET /v1/minimax/voices)."""
        url = f"{self.base_url}/v1/minimax/voices"
        try:
            res = self._request("GET", url, headers=self._get_headers(), timeout=15)
            res.raise_for_status()
            data = res.json()
            return data.get("voices", [])
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi lấy danh sách giọng MiniMax cloned: {e}")

    def list_capcut_system_voices(
        self,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 30,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        age: Optional[str] = None,
        emotion: Optional[str] = None,
        accent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tìm kiếm thư viện giọng hệ thống CapCut (GET /v1/capcut/system-voices)."""
        url = f"{self.base_url}/v1/capcut/system-voices"
        params: Dict[str, Any] = {
            "page": page,
            "page_size": page_size,
        }
        if search:
            params["search"] = search
        if language and language.lower() != "all":
            params["language"] = language
        if gender and gender.lower() != "all":
            params["gender"] = gender.capitalize()
        if age and age.lower() != "all":
            params["age"] = age
        if emotion and emotion.lower() != "all":
            params["emotion"] = emotion
        if accent and accent.lower() != "all":
            params["accent"] = accent

        try:
            res = self._request("GET", url, headers=self._get_headers(), params=params, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi tra cứu giọng CapCut: {e}")

    def list_community_voices(
        self,
        search: Optional[str] = None,
        limit: int = 30,
        offset: int = 0,
        gender: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy danh sách giọng cộng đồng Vibi (GET /v1/community/voices)."""
        url = f"{self.base_url}/v1/community/voices"
        params: Dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }
        if search:
            params["search"] = search
        if gender and gender.lower() != "all":
            params["gender"] = gender.lower()
        if language and language.lower() != "all":
            params["language"] = language.lower()

        try:
            res = self._request("GET", url, headers=self._get_headers(), params=params, timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi tra cứu giọng cộng đồng: {e}")

    def create_tts_task(
        self,
        voice_id: str,
        text: str,
        model_id: str = "eleven_v3",
        language_code: str = "vi",
        provider: str = "elevenlabs",
        voice_settings: Optional[Dict[str, Any]] = None,
        export_transcript: bool = False
    ) -> Dict[str, Any]:
        """Tạo tác vụ Text to Speech qua Vibi API (POST /v1/text-to-speech/{voice_id})."""
        url = f"{self.base_url}/v1/text-to-speech/{voice_id}"

        if voice_settings is None:
            if provider == "minimax":
                voice_settings = {
                    "speed": 1.0,
                    "pitch": 0,
                    "vol": 1.0
                }
            elif provider == "capcut":
                voice_settings = {
                    "speed": 1.0,
                    "pitch": 0
                }
            else:
                voice_settings = {
                    "stability": config.DEFAULT_VIBI_STABILITY,
                    "similarity_boost": config.DEFAULT_VIBI_SIMILARITY,
                    "speed": config.DEFAULT_VIBI_SPEED
                }

        payload: Dict[str, Any] = {
            "text": text,
            "language_code": language_code,
            "voice_settings": voice_settings,
            "export_transcript": export_transcript,
        }
        if provider != "capcut":
            payload["model_id"] = model_id
        if provider != "elevenlabs":
            payload["provider"] = provider

        try:
            res = self._request("POST", url, headers=self._get_headers(), json=payload, timeout=60)
            if res.status_code in (200, 201, 202):
                return res.json()

            try:
                err_data = res.json()
                msg = err_data.get("message") or err_data.get("error") or res.text
            except Exception:
                msg = res.text
            raise VibiAPIError(f"Tạo task TTS thất bại [HTTP {res.status_code}]: {msg}")
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi mạng khi gửi yêu cầu TTS: {e}")

    def get_task_detail(self, task_id: str) -> Dict[str, Any]:
        """Lấy chi tiết và trạng thái của tác vụ theo ID (GET /v1/history/{id})."""
        url = f"{self.base_url}/v1/history/{task_id}"
        try:
            res = self._request("GET", url, headers=self._get_headers(), timeout=15)
            res.raise_for_status()
            return res.json()
        except requests.RequestException as e:
            raise VibiAPIError(f"Lỗi khi kiểm tra tiến trình task {task_id}: {e}")

    def wait_for_task(
        self,
        task_id: str,
        timeout_sec: int = 180,
        poll_interval: float = 1.5,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Dict[str, Any]:
        """Chờ cho đến khi tác vụ hoàn thành (status == 'completed' hoặc 'failed')."""
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if is_cancelled and is_cancelled():
                raise VibiAPIError("Tác vụ đã bị người dùng hủy.")

            task = self.get_task_detail(task_id)
            status = task.get("status")

            if progress_callback:
                progress_callback(task)

            if status == "completed":
                return task
            elif status == "failed":
                err = task.get("error") or "Lỗi xử lý tác vụ từ server Voice API"
                raise VibiAPIError(f"Tác vụ {task_id} thất bại: {err}")

            # Chia nhỏ thời gian chờ để check hủy thường xuyên hơn
            waited = 0.0
            while waited < poll_interval:
                if is_cancelled and is_cancelled():
                    raise VibiAPIError("Tác vụ đã bị người dùng hủy.")
                time.sleep(0.2)
                waited += 0.2

        raise VibiAPIError(f"Quá thời gian chờ ({timeout_sec}s) cho tác vụ {task_id}!")

    def download_file(self, url: str, target_path: Path) -> Path:
        """Tải file từ URL về đường dẫn chỉ định."""
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with self._request("GET", url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(target_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            return target_path
        except Exception as e:
            raise VibiAPIError(f"Lỗi tải file từ {url}: {e}")

    def generate_and_download(
        self,
        text: str,
        voice_id: str,
        output_filename: Optional[str] = None,
        output_dir: Optional[Path] = None,
        model_id: str = "eleven_v3",
        language_code: str = "vi",
        provider: str = "elevenlabs",
        voice_settings: Optional[Dict[str, Any]] = None,
        export_transcript: bool = False,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Tuple[Optional[Path], Optional[Path]]:
        """Quy trình trọn gói: Gửi tạo TTS -> Chờ hoàn thành -> Tải file MP3 & Subtitle."""
        target_dir = output_dir or config.DOWNLOADS_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        task_data = self.create_tts_task(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            language_code=language_code,
            provider=provider,
            voice_settings=voice_settings,
            export_transcript=export_transcript
        )

        task_id = task_data.get("id")
        if not task_id:
            raise VibiAPIError("Phản hồi từ API không chứa Task ID!")

        completed_task = self.wait_for_task(
            task_id=task_id,
            progress_callback=progress_callback,
            is_cancelled=is_cancelled
        )

        result = completed_task.get("result", {})
        audio_url = result.get("audio_url")
        srt_url = result.get("srt_url")
        if not audio_url:
            raise VibiAPIError("Task hoàn thành nhưng không tìm thấy audio_url trong kết quả!")

        if not output_filename:
            clean_title = re.sub(r'[\\/*?:"<>|]', "", text[:25]).strip().replace(" ", "_")
            if not clean_title:
                clean_title = "vibi_voice"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{clean_title}_{timestamp}.mp3"
        elif not output_filename.endswith(".mp3"):
            output_filename += ".mp3"

        audio_path = target_dir / output_filename
        self.download_file(audio_url, audio_path)

        transcript_path: Optional[Path] = None
        transcript_url = srt_url
        srt_name = audio_path.stem + ".srt"
        candidate_srt = target_dir / srt_name
        if transcript_url:
            transcript_path = candidate_srt
            try:
                self.download_file(transcript_url, transcript_path)
            except Exception:
                transcript_path = candidate_srt if candidate_srt.exists() else None
        elif candidate_srt.exists():
            transcript_path = candidate_srt

        return audio_path, transcript_path

    @staticmethod
    def split_long_text(text: str, max_chars: int = 3500) -> List[str]:
        """Tách văn bản dài thành các đoạn nhỏ dưới giới hạn ký tự."""
        if len(text) <= max_chars:
            return [text]

        sentences = re.split(r'(?<=[.!?\n])\s+', text)
        chunks = []
        current_chunk = ""

        for sent in sentences:
            if len(current_chunk) + len(sent) + 1 <= max_chars:
                current_chunk += (" " if current_chunk else "") + sent
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sent

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

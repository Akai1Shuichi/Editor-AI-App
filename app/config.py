from pathlib import Path

from PyQt6.QtCore import QSettings


APP_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = APP_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
LEGACY_WATERMARK_DOWNLOADS_DIR = DOWNLOADS_DIR / "watermark"
LEGACY_TTS_DOWNLOADS_DIR = DOWNLOADS_DIR / "tts"

USER_DOWNLOADS_DIR = Path.home() / "Downloads"
USER_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
WATERMARK_DOWNLOADS_DIR = USER_DOWNLOADS_DIR / "watermark"
TTS_DOWNLOADS_DIR = USER_DOWNLOADS_DIR / "tts"
WATERMARK_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
TTS_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS = QSettings("AI Studio", "AI Media Studio")


def _get_projects_dir() -> Path:
    """Return the default projects directory for the current user."""
    desktop = Path.home() / "Desktop"
    projects = (
        desktop / "Editor-AI-Projects"
        if desktop.exists()
        else Path.home() / "Editor-AI-Projects"
    )
    projects.mkdir(parents=True, exist_ok=True)
    return projects


def _setting_text(key: str, default: str) -> str:
    value = SETTINGS.value(key, default)
    return str(value) if value is not None else default


def _setting_float(key: str, default: float) -> float:
    try:
        return float(SETTINGS.value(key, default))
    except (TypeError, ValueError):
        return default


def reload_config():
    """Load the app configuration exclusively from QSettings."""
    global VIBI_API_BASE, VIBI_API_KEY, DEFAULT_VIBI_MODEL, DEFAULT_VIBI_LANGUAGE
    global DEFAULT_VIBI_VOICE_ID, DEFAULT_VIBI_STABILITY, DEFAULT_VIBI_SIMILARITY
    global DEFAULT_VIBI_SPEED, ACTIVE_PROJECT, PROJECTS_DIR

    projects_value = _setting_text("PROJECTS_DIR", "")
    PROJECTS_DIR = Path(projects_value) if projects_value else _get_projects_dir()
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_PROJECT = _setting_text("ACTIVE_PROJECT", "")
    VIBI_API_BASE = _setting_text("VIBI_API_BASE", "https://api.vibi.pro")
    VIBI_API_KEY = _setting_text("VIBI_API_KEY", "")
    DEFAULT_VIBI_MODEL = _setting_text("DEFAULT_VIBI_MODEL", "eleven_v3")
    DEFAULT_VIBI_LANGUAGE = _setting_text("DEFAULT_VIBI_LANGUAGE", "vi")
    DEFAULT_VIBI_VOICE_ID = _setting_text(
        "DEFAULT_VIBI_VOICE_ID", "6adFm46eyy74snVn6YrT"
    )
    DEFAULT_VIBI_STABILITY = _setting_float("DEFAULT_VIBI_STABILITY", 0.5)
    DEFAULT_VIBI_SIMILARITY = _setting_float("DEFAULT_VIBI_SIMILARITY", 0.75)
    DEFAULT_VIBI_SPEED = _setting_float("DEFAULT_VIBI_SPEED", 1.0)


def save_setting(key: str, value: str) -> None:
    """Persist one application setting and refresh the in-memory values."""
    SETTINGS.setValue(key, str(value))
    SETTINGS.sync()
    reload_config()


reload_config()

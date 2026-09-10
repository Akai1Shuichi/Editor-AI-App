import os
from pathlib import Path
from dotenv import load_dotenv

# Thư mục gốc của project (editor video app)
APP_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = APP_DIR / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

ENV_FILE = APP_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)

# Cấu hình Vibi API mặc định
VIBI_API_BASE = os.getenv("VIBI_API_BASE", "https://api.vibi.pro")
VIBI_API_KEY = os.getenv("VIBI_API_KEY", "")
DEFAULT_VIBI_MODEL = os.getenv("DEFAULT_VIBI_MODEL", "eleven_v3")
DEFAULT_VIBI_LANGUAGE = os.getenv("DEFAULT_VIBI_LANGUAGE", "vi")
DEFAULT_VIBI_VOICE_ID = os.getenv("DEFAULT_VIBI_VOICE_ID", "6adFm46eyy74snVn6YrT")
DEFAULT_VIBI_STABILITY = float(os.getenv("DEFAULT_VIBI_STABILITY", "0.5"))
DEFAULT_VIBI_SIMILARITY = float(os.getenv("DEFAULT_VIBI_SIMILARITY", "0.75"))
DEFAULT_VIBI_SPEED = float(os.getenv("DEFAULT_VIBI_SPEED", "1.0"))

def reload_config():
    global VIBI_API_BASE, VIBI_API_KEY, DEFAULT_VIBI_MODEL, DEFAULT_VIBI_LANGUAGE, DEFAULT_VIBI_VOICE_ID
    global DEFAULT_VIBI_STABILITY, DEFAULT_VIBI_SIMILARITY, DEFAULT_VIBI_SPEED
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=True)
    VIBI_API_BASE = os.getenv("VIBI_API_BASE", "https://api.vibi.pro")
    VIBI_API_KEY = os.getenv("VIBI_API_KEY", "")
    DEFAULT_VIBI_MODEL = os.getenv("DEFAULT_VIBI_MODEL", "eleven_v3")
    DEFAULT_VIBI_LANGUAGE = os.getenv("DEFAULT_VIBI_LANGUAGE", "vi")
    DEFAULT_VIBI_VOICE_ID = os.getenv("DEFAULT_VIBI_VOICE_ID", "6adFm46eyy74snVn6YrT")
    DEFAULT_VIBI_STABILITY = float(os.getenv("DEFAULT_VIBI_STABILITY", "0.5"))
    DEFAULT_VIBI_SIMILARITY = float(os.getenv("DEFAULT_VIBI_SIMILARITY", "0.75"))
    DEFAULT_VIBI_SPEED = float(os.getenv("DEFAULT_VIBI_SPEED", "1.0"))

def save_env_variable(key: str, value: str):
    """Lưu hoặc cập nhật biến cấu hình vào file .env và nạp lại runtime."""
    os.environ[key] = str(value)
    lines = []
    found = False
    if ENV_FILE.exists():
        lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            line_str = line.strip()
            if line_str.startswith(f"{key}=") or line_str.startswith(f"{key} ="):
                lines[i] = f"{key}={value}"
                found = True
                break
    if not found:
        lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    reload_config()

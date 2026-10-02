import os
from pathlib import Path
from dotenv import load_dotenv
import imageio_ffmpeg

# Project Root Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Output Directory
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

class Config:
    @staticmethod
    def get_gemini_key() -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @staticmethod
    def get_suno_key() -> str:
        return os.getenv("APIFRAME_SUNO_KEY", "")

    @staticmethod
    def get_nano_key() -> str:
        return os.getenv("APIFRAME_NANO_KEY", "")

    @staticmethod
    def set_keys(gemini_key: str, suno_key: str, nano_key: str):
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"GEMINI_API_KEY={gemini_key}\n")
            f.write(f"APIFRAME_SUNO_KEY={suno_key}\n")
            f.write(f"APIFRAME_NANO_KEY={nano_key}\n")
        # Reload
        load_dotenv(ENV_FILE, override=True)

    @staticmethod
    def get_ffmpeg_path() -> str:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

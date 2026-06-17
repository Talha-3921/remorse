import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "output"
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "gpt-image-1").strip() or "gpt-image-1"
FALLBACK_IMAGE_MODEL = "dall-e-2"
REASONING_MODEL = os.getenv("REASONING_MODEL", "gpt-4o").strip() or "gpt-4o"
FAST_MODEL = os.getenv("FAST_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
TTS_MODEL = os.getenv("TTS_MODEL", "gpt-4o-mini-tts").strip() or "gpt-4o-mini-tts"

WCAG_PROMPT = (
    "high-contrast schematic illustration, WCAG AA compliant, minimum 4.5:1 "
    "contrast ratio between foreground and background, minimal clutter, no fine "
    "print, bold numbered steps, clear icons."
)


def require_api_key() -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Create edushield/.env from .env.example "
            "and set OPENAI_API_KEY before running EduShield."
        )
    return OPENAI_API_KEY


def get_client() -> OpenAI:
    return OpenAI(api_key=require_api_key())


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

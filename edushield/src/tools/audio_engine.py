import re
from copy import deepcopy
from pathlib import Path

from gtts import gTTS

from src.config import settings
from src.tools.translate import translate_to_urdu


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "category"


def _write_openai_audio(response, out_path: Path) -> None:
    if hasattr(response, "write_to_file"):
        response.write_to_file(out_path)
        return
    if hasattr(response, "stream_to_file"):
        response.stream_to_file(out_path)
        return
    content = getattr(response, "content", None)
    if content:
        out_path.write_bytes(content)
        return
    raise RuntimeError("OpenAI audio response did not expose writable content.")


def synthesize_speech(text: str, out_path: str, gtts_lang: str) -> str | None:
    """OpenAI TTS to gTTS fallback. Returns None when audio is unavailable."""
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not text.strip():
        return None
    try:
        client = settings.get_client()
        response = client.audio.speech.create(
            model=settings.TTS_MODEL,
            voice="alloy",
            input=text[:3900],
        )
        _write_openai_audio(response, target)
        return str(target)
    except Exception as exc:
        print(f"[audio] OpenAI TTS fallback: {type(exc).__name__}: {exc}")
    try:
        gTTS(text=text, lang=gtts_lang).save(str(target))
        return str(target)
    except Exception as exc:
        print(f"[audio] gTTS unavailable: {type(exc).__name__}: {exc}")
        return None


def generate_audio_pair(category: dict) -> dict:
    """Generate English and Urdu narration files for one category."""
    updated = deepcopy(category)
    title = str(updated.get("category_title", "category"))
    slug = _slug(title)
    script_en = str(updated.get("grounded_script", "Review your public exposure manually."))
    script_ur = translate_to_urdu(script_en)
    urdu_is_fallback = script_ur is None
    if script_ur is None:
        script_ur = "Urdu audio unavailable; English guidance follows. " + script_en

    audio_en = synthesize_speech(script_en, str(settings.OUTPUT_DIR / f"{slug}_en.mp3"), "en")
    audio_ur = synthesize_speech(script_ur, str(settings.OUTPUT_DIR / f"{slug}_ur.mp3"), "ur")
    updated["audio_en"] = audio_en
    updated["audio_ur"] = audio_ur
    updated["urdu_text"] = script_ur
    updated["urdu_is_fallback"] = urdu_is_fallback
    updated["agent_notes"] = updated.get("agent_notes", []) + ["Audio engine generated EN/UR narration or fallback labels."]
    return updated


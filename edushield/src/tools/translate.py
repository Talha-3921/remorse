from src.config.settings import FAST_MODEL, get_client


def translate_to_urdu(english_text: str) -> str | None:
    """Translate English guidance to natural Urdu script. None on failure."""
    if not english_text.strip():
        return None
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "Translate to natural Urdu script. Return only the Urdu text.",
                },
                {"role": "user", "content": english_text},
            ],
            temperature=0.2,
        )
        text = (response.choices[0].message.content or "").strip()
        return text or None
    except Exception as exc:
        print(f"[translate] Urdu fallback: {type(exc).__name__}: {exc}")
        return None


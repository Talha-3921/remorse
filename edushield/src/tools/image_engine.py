import base64
import re
import textwrap
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont

from src.config import settings


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "category"


def _image_from_response(response, out_path: Path) -> bool:
    data = response.data[0]
    b64_value = getattr(data, "b64_json", None)
    url = getattr(data, "url", None)
    if b64_value:
        out_path.write_bytes(base64.b64decode(b64_value))
        return True
    if url:
        with urlopen(url, timeout=30) as remote:
            out_path.write_bytes(remote.read())
        return True
    return False


def _fallback_card(category: dict, out_path: Path) -> str:
    title = str(category.get("category_title", "Privacy Card"))
    findings = category.get("findings", [])[:2]
    steps = category.get("remediation_steps", [])[:3]
    image = Image.new("RGB", (1024, 1024), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 50)
        body_font = ImageFont.truetype("arial.ttf", 30)
    except Exception:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()
    draw.rectangle((0, 0, 1024, 150), fill="#06283D")
    draw.text((48, 44), title[:34], fill="white", font=title_font)
    y = 190
    evidence = [
        f"{item.get('site_name', 'site')}: {item.get('title', '')}" for item in findings
    ] or category.get("dorks", [])[:2]
    blocks = [
        ("1. Evidence found", evidence),
        ("2. Verify exact match", steps[:1]),
        ("3. Request removal", steps[1:] or steps),
    ]
    for heading, lines in blocks:
        draw.rounded_rectangle((48, y, 976, y + 218), radius=18, outline="#06283D", width=5, fill="#F7FAFC")
        draw.text((80, y + 26), heading, fill="#06283D", font=body_font)
        text = " | ".join(str(x) for x in lines) or "Use exact details and official removal channels."
        wrapped = textwrap.wrap(text, width=44)[:3]
        for idx, line in enumerate(wrapped):
            draw.text((80, y + 78 + (idx * 34)), line, fill="#111111", font=body_font)
        y += 248
    out_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(out_path)
    return str(out_path)


def generate_visual_card(category: dict, style_prefix: str) -> str:
    """Generate one visual card with OpenAI image fallback chain to PIL."""
    title = str(category.get("category_title", "privacy-card"))
    out_path = settings.OUTPUT_DIR / f"{_slug(title)}_visual.png"
    dork_preview = "\n".join(category.get("dorks", [])[:4])
    finding_preview = "\n".join(
        f"{item.get('site_name', 'site')} score {item.get('match_score', 0)}: {item.get('title', '')}"
        for item in category.get("findings", [])[:4]
    )
    steps = "\n".join(str(x) for x in category.get("remediation_steps", [])[:4])
    prompt = (
        f"{style_prefix}\n{settings.WCAG_PROMPT}\n"
        f"Create a privacy remediation dork card for Pakistani university students.\n"
        f"Category: {title}\n"
        f"Include bold numbered steps: 1 Search manually, 2 Verify exact match, 3 Request removal, 4 Re-check.\n"
        f"Use these search evidence hints without tiny text: {finding_preview or dork_preview}\n"
        f"Remediation summary: {steps}"
    )
    category["image_prompt"] = prompt
    for model in [settings.IMAGE_MODEL, settings.FALLBACK_IMAGE_MODEL]:
        try:
            client = settings.get_client()
            response = client.images.generate(model=model, prompt=prompt, size="1024x1024")
            if _image_from_response(response, out_path):
                return str(out_path)
        except Exception as exc:
            print(f"[image] {model} fallback: {type(exc).__name__}: {exc}")
    return _fallback_card(category, out_path)

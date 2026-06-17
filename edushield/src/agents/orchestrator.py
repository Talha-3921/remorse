import json
import time
from copy import deepcopy

from src.config import settings
from src.parsers.deconstructor import deconstruct_exposures, parse_user_info
from src.tools.audio_engine import generate_audio_pair
from src.tools.dork_generator import generate_dorks
from src.tools.grounding import ground_category
from src.tools.image_engine import generate_visual_card


MISUSE_TERMS = {
    "hack someone",
    "steal",
    "dump database",
    "bypass",
    "password list",
    "exploit",
    "dox",
}


def _looks_like_misuse(user_input: str) -> bool:
    lower = user_input.lower()
    return any(term in lower for term in MISUSE_TERMS)


def _fallback_checklist(category: dict) -> dict:
    return {
        "items": [
            {
                "step": "Manual search",
                "action": "Paste at least two dorks into Google and mark whether exact personal details appear.",
            },
            {
                "step": "Removal request",
                "action": "Send the exposed URL and screenshot to the university or site owner for removal.",
            },
            {
                "step": "Re-check",
                "action": "Repeat the same dorks after 3-7 days and record whether the exposure disappeared.",
            },
        ]
    }


def generate_checklist(category: dict) -> dict:
    """Generate a 2-3 item verification/remediation checklist."""
    try:
        client = settings.get_client()
        response = client.chat.completions.create(
            model=settings.FAST_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only JSON: {\"items\":[{\"step\":str,\"action\":str}]}. "
                        "Create 2-3 ethical verification/remediation checklist items."
                    ),
                },
                {"role": "user", "content": json.dumps(category, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        items = data.get("items", [])
        if not isinstance(items, list) or not (2 <= len(items) <= 3):
            raise ValueError("Checklist must contain 2-3 items.")
        return {"items": items[:3]}
    except Exception as exc:
        print(f"[checklist] fallback: {type(exc).__name__}: {exc}")
        return _fallback_checklist(category)


def run_pipeline(user_input: str) -> dict:
    """Run the deterministic per-category EduShield pipeline."""
    start = time.time()
    trace: list[str] = []
    if _looks_like_misuse(user_input):
        raise ValueError(
            "EduShield only supports checking your own public exposure. It cannot help with stealing, doxing, bypassing access controls, or targeting others."
        )

    trace.append("Pipeline started.")
    user_info = parse_user_info(user_input)
    categories = deconstruct_exposures(user_info)
    trace.append(f"Deconstructor produced {len(categories)} categories.")
    style_prefix = (
        "Use a clean civic-tech visual style for Pakistani university privacy guidance: "
        "white background, navy headings, amber warnings, green verified actions."
    )

    final_categories = []
    for index, category in enumerate(categories, start=1):
        current = deepcopy(category)
        trace.append(f"[{index}/{len(categories)}] {current['category_title']}: dork generator started.")
        current = generate_dorks(current)
        trace.append(f"[{index}/{len(categories)}] generated {len(current.get('dorks', []))} dorks.")
        current = ground_category(current)
        visual_path = generate_visual_card(current, style_prefix)
        current["visual_path"] = visual_path
        current = generate_audio_pair(current)
        current["checklist"] = generate_checklist(current)
        final_categories.append(current)
        trace.append(
            f"[{index}/{len(categories)}] completed visual={bool(visual_path)}, "
            f"audio_en={bool(current.get('audio_en'))}, audio_ur={bool(current.get('audio_ur'))}."
        )

    runtime = round(time.time() - start, 2)
    visual_count = sum(1 for item in final_categories if item.get("visual_path"))
    audio_count = sum(1 for item in final_categories for key in ("audio_en", "audio_ur") if item.get(key))
    trace.append(f"Runtime seconds: {runtime}")
    trace.append(f"Count check: categories={len(final_categories)}, visuals={visual_count}, audios={audio_count}.")
    return {
        "categories": final_categories,
        "trace": trace,
        "runtime_seconds": runtime,
        "ethical_warning": (
            "Manual public search only. Do not scrape, bypass logins, access private accounts, or investigate other people without consent."
        ),
    }


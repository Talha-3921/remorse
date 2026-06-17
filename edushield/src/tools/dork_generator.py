import json
import re
from copy import deepcopy

from src.config import settings


def _clean_json_array(text: str) -> list:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.I).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1:
        stripped = stripped[start : end + 1]
    value = json.loads(stripped)
    if not isinstance(value, list):
        raise ValueError("Dork agent did not return a JSON array.")
    return value


def _normalize_dorks(items: list) -> list[str]:
    dorks: list[str] = []
    for item in items:
        if isinstance(item, dict):
            query = str(item.get("query", "")).strip()
        else:
            query = str(item).strip()
        query = re.sub(r"\s+", " ", query)
        if not query or len(query) < 8:
            continue
        lowered = query.lower()
        if lowered.startswith("http://") or lowered.startswith("https://"):
            continue
        if query not in dorks:
            dorks.append(query)
    if len(dorks) < 10:
        raise ValueError("Dork agent returned fewer than 10 usable queries.")
    return dorks[:18]


def generate_dorks(category: dict) -> dict:
    """Use an AI dork researcher to generate runtime Google dorks for one category."""
    updated = deepcopy(category)
    full_context = str(updated.get("full_user_context") or updated.get("raw_context") or "")
    prompt = {
        "role": "dork_researcher",
        "category": updated,
        "full_user_context": full_context,
        "instructions": [
            "Generate Google dorks at runtime from the user's messy/garbled context.",
            "Do not use placeholder words like name, email, cnic, university unless the user literally provided that exact value.",
            "Use exact values and combinations from the full context, including likely spelling variants.",
            "Use advanced operators: quoted phrases, filetype:pdf/xlsx/docx/csv, site:, inurl:, intitle:, related public platforms, Google Drive/docs, GitHub, admissions/results/merit portals.",
            "Prefer legal public search queries only. No scraping, login bypass, exploit terms, or instructions to access private systems.",
            "Return only JSON array strings. No markdown.",
        ],
    }
    try:
        client = settings.get_client()
        response = client.chat.completions.create(
            model=settings.REASONING_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an ethical OSINT search-query specialist for personal data exposure checks. "
                        "Return only a JSON array of 10 to 18 Google search queries."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.55,
        )
        dorks = _normalize_dorks(_clean_json_array(response.choices[0].message.content or "[]"))
        source = "ai_generated"
    except Exception as exc:
        print(f"[dork_generator] AI fallback: {type(exc).__name__}: {exc}")
        # This fallback is intentionally minimal and clearly marked; normal operation is AI-generated.
        safe_context = " ".join(re.findall(r"[A-Za-z0-9@._-]{4,}", full_context))[:220]
        dorks = [
            f'"{safe_context}"',
            f'"{safe_context}" filetype:pdf',
            f'"{safe_context}" site:edu.pk',
            f'"{safe_context}" site:drive.google.com',
            f'"{safe_context}" site:github.com',
            f'"{safe_context}" inurl:uploads',
            f'"{safe_context}" inurl:result',
            f'"{safe_context}" intitle:"index of"',
            f'"{safe_context}" filetype:xlsx',
            f'"{safe_context}" filetype:docx',
        ]
        source = "emergency_context_fallback"
    updated["dorks"] = dorks
    updated["dork_source"] = source
    updated["agent_notes"] = updated.get("agent_notes", []) + [
        f"Dork Researcher generated {len(dorks)} runtime queries from full user context."
    ]
    return updated

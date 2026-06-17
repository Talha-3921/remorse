import json
import re
from typing import Any

from src.config.settings import REASONING_MODEL, get_client


def parse_user_info(user_input: str) -> str:
    """Clean and structure the raw user text/voice input. Log character count."""
    cleaned = re.sub(r"\s+", " ", (user_input or "").strip())
    print(f"[deconstructor] cleaned user input characters={len(cleaned)}")
    if not cleaned:
        raise ValueError("Please enter your own details before running the audit.")
    return cleaned


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1 and end > start:
        return stripped[start : end + 1]
    return stripped


def _validate_categories(value: Any) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise ValueError("Exposure decomposition returned no categories.")
    categories: list[dict] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Category {idx} is not an object.")
        title = str(item.get("category_title", "")).strip()
        key_pii = item.get("key_pii", [])
        raw_context = str(item.get("raw_context", "")).strip()
        if not title:
            raise ValueError(f"Category {idx} is missing category_title.")
        if not isinstance(key_pii, list):
            key_pii = [str(key_pii)]
        normalized = {
            "category_title": title,
            "key_pii": [str(x).strip() for x in key_pii if str(x).strip()],
            "raw_context": raw_context or title,
        }
        categories.append(normalized)
    return categories


def _heuristic_categories(user_info: str) -> list[dict]:
    lower = user_info.lower()
    categories = []
    checks = [
        ("CNIC in PDFs and Spreadsheets", ["cnic", "identity number"], ["cnic"]),
        ("University Documents and Portals", ["university", "student id", "roll"], ["university", "student", "roll"]),
        ("Academic Records and Result Sheets", ["result", "marksheet", "transcript"], ["result", "marks", "transcript"]),
        ("Contact Details in Public Pages", ["email", "phone", "mobile"], ["email", "phone", "mobile", "@"]),
        ("Metadata Leaks in Shared Files", ["metadata", "drive", "pdf", "docx"], ["drive", "pdf", "docx", "xlsx"]),
        ("Name and Family Detail Matches", ["name", "father"], ["name", "father"]),
    ]
    for title, pii_labels, needles in checks:
        if any(needle in lower for needle in needles):
            categories.append(
                {
                    "category_title": title,
                    "key_pii": pii_labels,
                    "raw_context": user_info[:500],
                }
            )
    if not categories:
        categories.append(
            {
                "category_title": "General Personal Information Exposure",
                "key_pii": ["name", "student details", "contact or academic identifiers"],
                "raw_context": user_info[:500],
            }
        )
    return categories[:6]


def deconstruct_exposures(user_info: str) -> list[dict]:
    """Send to gpt-4o and return validated exposure categories."""
    prompt = f"""
Return ONLY a raw JSON array. No markdown.
Decompose this Pakistani university student privacy input into distinct exposure
categories. Each array item must have:
category_title: string
key_pii: list of short strings
raw_context: short summary for this category

Make categories specific and non-overlapping. Keep 2 to 6 categories.

User input:
{user_info}
"""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model=REASONING_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a privacy analyst. Output only valid JSON arrays.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        data = json.loads(_strip_json_fence(content))
        return _validate_categories(data)
    except Exception as exc:
        print(f"[deconstructor] model fallback: {type(exc).__name__}: {exc}")
        return _validate_categories(_heuristic_categories(user_info))


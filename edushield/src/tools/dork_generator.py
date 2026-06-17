import re
from copy import deepcopy


def _quoted_terms(values: list[str]) -> list[str]:
    terms = []
    for value in values:
        for piece in re.split(r"[,;|]", value):
            cleaned = piece.strip()
            if cleaned and len(cleaned) <= 80:
                terms.append(f'"{cleaned}"')
    return terms[:8]


def _guess_university(context: str) -> str:
    match = re.search(r"(?:university|uni)\s*[:\-]?\s*([A-Za-z0-9 .&'-]{3,80})", context, re.I)
    if match:
        return match.group(1).strip()
    return "university"


def generate_dorks(category: dict) -> dict:
    """Generate 10+ advanced, manual Google dorks for one exposure category."""
    updated = deepcopy(category)
    title = str(updated.get("category_title", "Privacy Exposure")).strip()
    context = str(updated.get("raw_context", ""))
    pii = [str(x) for x in updated.get("key_pii", [])]
    terms = _quoted_terms(pii + [context])
    primary = terms[0] if terms else f'"{title}"'
    university = _guess_university(context)
    uni_q = f'"{university}"' if university != "university" else '"university"'

    templates = [
        f'{primary} filetype:pdf site:edu.pk',
        f'{primary} filetype:xlsx OR filetype:xls site:edu.pk',
        f'{primary} filetype:docx OR filetype:doc site:edu.pk',
        f'{primary} intitle:"index of" "student" OR "students"',
        f'{primary} inurl:uploads site:edu.pk',
        f'{primary} inurl:results OR inurl:result site:edu.pk',
        f'{primary} inurl:admission OR inurl:merit site:edu.pk',
        f'{primary} {uni_q} "CNIC" OR "B-Form"',
        f'{primary} {uni_q} "DOB" OR "date of birth"',
        f'{primary} {uni_q} "student id" OR "roll no"',
        f'{primary} site:drive.google.com "view" OR "folders"',
        f'{primary} site:docs.google.com "spreadsheet" OR "document"',
        f'{primary} site:github.com "CNIC" OR "student"',
        f'{primary} "metadata" filetype:pdf site:edu.pk',
        f'{primary} cache:{university.replace(" ", "").lower()}.edu.pk',
    ]
    dorks = []
    for dork in templates:
        normalized = re.sub(r"\s+", " ", dork).strip()
        if normalized not in dorks:
            dorks.append(normalized)

    updated["dorks"] = dorks[:15]
    updated["agent_notes"] = updated.get("agent_notes", []) + [
        f"Dork Generator created {len(updated['dorks'])} manual search queries for {title}."
    ]
    return updated


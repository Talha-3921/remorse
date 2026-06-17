import json
import re
from copy import deepcopy
from html import unescape
from urllib.error import HTTPError
from urllib.parse import quote_plus, urlparse
from urllib.request import urlopen

from src.config import settings


def _tokens(text: str) -> set[str]:
    values = set()
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9@._-]{2,}", text.lower()):
        if token not in {"name", "email", "phone", "university", "student", "cnic", "dob"}:
            values.add(token)
    return values


def _extract_meta(item: dict) -> dict:
    pagemap = item.get("pagemap") or {}
    metatags = pagemap.get("metatags") or []
    meta = metatags[0] if metatags and isinstance(metatags[0], dict) else {}
    return {
        "description": meta.get("og:description") or meta.get("description") or "",
        "site_name": meta.get("og:site_name") or "",
        "type": meta.get("og:type") or "",
    }


def _site_name(url: str, meta: dict) -> str:
    if meta.get("site_name"):
        return str(meta["site_name"])
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host or "unknown site"


def google_search(query: str, num: int | None = None) -> list[dict]:
    """Run one Google Custom Search JSON API query. No HTML scraping."""
    if not settings.GOOGLE_API_KEY or not settings.GOOGLE_CSE_ID:
        raise RuntimeError("Google Custom Search is not configured. Set GOOGLE_API_KEY and GOOGLE_CSE_ID.")
    count = max(1, min(num or settings.SEARCH_RESULTS_PER_DORK, 10))
    url = (
        "https://www.googleapis.com/customsearch/v1"
        f"?key={quote_plus(settings.GOOGLE_API_KEY)}"
        f"&cx={quote_plus(settings.GOOGLE_CSE_ID)}"
        f"&q={quote_plus(query)}"
        f"&num={count}"
        "&safe=active"
    )
    try:
        with urlopen(url, timeout=25) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            detail = payload.get("error", {}).get("message", "")
        except Exception:
            detail = str(exc)
        raise RuntimeError(f"Google Custom Search API error {exc.code}: {detail}") from exc
    results = []
    for item in payload.get("items", []):
        meta = _extract_meta(item)
        link = str(item.get("link", ""))
        results.append(
            {
                "query": query,
                "title": unescape(str(item.get("title", ""))),
                "url": link,
                "site_name": _site_name(link, meta),
                "snippet": unescape(str(item.get("snippet", ""))),
                "html_snippet": str(item.get("htmlSnippet", "")),
                "meta_description": unescape(str(meta.get("description", ""))),
                "file_format": item.get("fileFormat", ""),
                "mime": item.get("mime", ""),
            }
        )
    return results


def score_result(result: dict, category: dict) -> dict:
    """Score a search result against full user context and category PII."""
    full_context = str(category.get("full_user_context") or category.get("raw_context") or "")
    key_pii = " ".join(str(x) for x in category.get("key_pii", []))
    haystack = " ".join(
        str(result.get(key, ""))
        for key in ["title", "url", "snippet", "meta_description", "file_format", "mime"]
    ).lower()
    context_tokens = _tokens(full_context)
    pii_tokens = _tokens(key_pii)
    matched_context = sorted(token for token in context_tokens if token in haystack)
    matched_pii = sorted(token for token in pii_tokens if token in haystack)
    score = min(100, (len(matched_context) * 14) + (len(matched_pii) * 22))
    reason = "No strong snippet/meta match"
    if score >= 60:
        reason = "Strong match against multiple user-context tokens"
    elif score >= 30:
        reason = "Possible match; verify manually before acting"
    return {
        **result,
        "match_score": score,
        "matched_context_terms": matched_context[:12],
        "matched_pii_terms": matched_pii[:12],
        "match_reason": reason,
    }


def search_category(category: dict) -> dict:
    """Search top dorks and attach snippet/meta matched findings."""
    updated = deepcopy(category)
    all_results = []
    errors = []
    for dork in updated.get("dorks", [])[: settings.MAX_DORKS_TO_SEARCH]:
        try:
            all_results.extend(google_search(dork))
        except Exception as exc:
            errors.append(f"{dork}: {type(exc).__name__}: {exc}")

    seen = set()
    scored = []
    for result in all_results:
        url = result.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        scored.append(score_result(result, updated))
    scored.sort(key=lambda item: item.get("match_score", 0), reverse=True)
    findings = [item for item in scored if item.get("match_score", 0) >= 30]
    if not findings:
        findings = scored[: min(3, len(scored))]

    updated["search_configured"] = bool(settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID)
    updated["search_errors"] = errors[:5]
    updated["search_results_checked"] = len(scored)
    updated["findings"] = findings[: settings.MAX_FINDINGS_PER_CATEGORY]
    updated["agent_notes"] = updated.get("agent_notes", []) + [
        f"Search Researcher checked {len(scored)} Google results and kept {len(updated['findings'])} findings."
    ]
    return updated

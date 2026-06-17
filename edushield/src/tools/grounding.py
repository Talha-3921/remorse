import json
from copy import deepcopy
from urllib.parse import urlparse

from src.config.settings import FAST_MODEL, get_client


def _host(url: str) -> str:
    return urlparse(url).netloc.lower().replace("www.", "") or "the site owner"


def _fallback_grounding(category: dict) -> dict:
    findings = category.get("findings", [])
    top = findings[0] if findings else {}
    host = _host(str(top.get("url", "")))
    title = category.get("category_title", "this exposure")
    if findings:
        script = (
            f"For {title}, Google snippets show possible exposure on {host}. "
            "Treat this as a lead, not proof: open the result manually, confirm the exact personal details, "
            "save the URL and screenshot, then request removal from the page owner and Google de-indexing."
        )
        remediation = [
            f"Open the matched result on {host} and verify the exact fields shown in the snippet or page.",
            f"Find {host}'s privacy, webmaster, registrar, or contact page and request removal/redaction of the specific URL.",
            "After the page owner removes it, use Google's outdated content/removal tools to refresh the cached snippet.",
            "Re-run the same dork after 3-7 days and keep evidence of the request.",
        ]
    else:
        script = (
            f"For {title}, no strong Google snippet match was returned by the configured search. "
            "Keep the generated dorks for manual checks, broaden spelling variants, and re-run later."
        )
        remediation = [
            "Manually test the top dorks in Google and verify exact matches only.",
            "If a match appears, capture the URL, snippet, and exposed fields.",
            "Contact the site owner for removal and then request Google cache/snippet refresh.",
        ]
    return {
        "grounded_script": script,
        "remediation_steps": remediation,
        "verification_steps": [
            "Confirm the result belongs to you and not a similar name.",
            "Compare title, URL, snippet, and meta description against your full input.",
            "Track removal request date, contact channel, and follow-up date.",
        ],
        "risk_summary": "Search snippets are leads and must be manually verified before action.",
        "site_policy_research": [
            {
                "site": host,
                "policy_queries": [
                    f'site:{host} privacy policy personal information removal',
                    f'site:{host} contact webmaster remove personal data',
                    f'site:{host} DMCA privacy complaint data removal',
                ],
                "removal_route": f"Contact {host} privacy/webmaster support with the exact URL and exposed fields.",
            }
        ]
        if findings
        else [],
        "unverified": True,
    }


def ground_category(category: dict) -> dict:
    """Research findings and produce site-specific remediation guidance."""
    updated = deepcopy(category)
    try:
        client = get_client()
        prompt = {
            "role": "remediation_researcher",
            "category": updated.get("category_title"),
            "full_user_context": updated.get("full_user_context"),
            "key_pii": updated.get("key_pii", []),
            "dorks": updated.get("dorks", [])[:8],
            "findings": updated.get("findings", []),
            "task": (
                "Use only the Google result title/url/snippet/meta fields provided. Do not invent confirmed exposure. "
                "Decide which findings look like possible matches against the whole user context. For each distinct site, "
                "produce policy research queries and practical removal route. Return JSON."
            ),
            "required_json": {
                "grounded_script": "2-4 sentence narration for this category",
                "risk_summary": "short summary",
                "remediation_steps": ["specific removal actions"],
                "verification_steps": ["2-4 exact verification actions"],
                "site_policy_research": [
                    {
                        "site": "domain or site name",
                        "evidence_url": "matched URL if available",
                        "why_it_matches": "snippet/meta/context reason",
                        "policy_queries": ["queries to research removal policy"],
                        "removal_route": "site-specific recommended route",
                    }
                ],
            },
        }
        response = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an ethical privacy-removal researcher. Return only valid JSON. "
                        "Be precise, site-specific, and never claim a confirmed leak unless snippet/meta strongly supports it."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0.25,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        updated["grounded_script"] = str(data.get("grounded_script", "")).strip()
        updated["risk_summary"] = str(data.get("risk_summary", "")).strip()
        updated["remediation_steps"] = list(data.get("remediation_steps", []))[:6]
        updated["verification_steps"] = list(data.get("verification_steps", []))[:5]
        updated["site_policy_research"] = list(data.get("site_policy_research", []))[:5]
        updated["unverified"] = True
        if not updated["grounded_script"] or not updated["remediation_steps"]:
            raise ValueError("Remediation researcher returned incomplete guidance.")
    except Exception as exc:
        print(f"[grounding] fallback: {type(exc).__name__}: {exc}")
        updated.update(_fallback_grounding(updated))
    updated["agent_notes"] = updated.get("agent_notes", []) + [
        "Remediation Researcher used snippet/meta findings to produce site-specific removal guidance."
    ]
    return updated

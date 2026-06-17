import json
from copy import deepcopy

from src.config.settings import FAST_MODEL, get_client


def _fallback_grounding(category: dict) -> dict:
    dorks = category.get("dorks", [])
    first = dorks[0] if dorks else "one exact-name query"
    return {
        "grounded_script": (
            f"For {category.get('category_title', 'this exposure')}, copy one dork at a time into Google manually, "
            f"starting with {first}. Open only results that appear to be official public pages, PDFs, Drive links, "
            "or university upload folders, then confirm whether the page contains your own details before taking screenshots. "
            "If a match is real, contact the university office, site owner, or Google removal flow and ask for the file to be removed or de-indexed."
        ),
        "remediation_steps": [
            "Document the public URL, screenshot, and exact exposed fields.",
            "Request removal from the university/site owner and ask for Google Search Console de-indexing.",
            "Re-check the same dorks after 3-7 days and keep a dated record.",
        ],
        "verification_steps": [
            "Search the top dorks manually in a private browser window.",
            "Confirm whether the result contains your exact details, not another person.",
            "Record the removal request date and follow-up owner.",
        ],
        "risk_summary": "Unverified until the user manually checks public search results.",
        "unverified": True,
    }


def ground_category(category: dict) -> dict:
    """Create narration/remediation script and verification steps for one category."""
    updated = deepcopy(category)
    try:
        client = get_client()
        prompt = json.dumps(
            {
                "category": updated,
                "task": (
                    "Return JSON with grounded_script, remediation_steps, verification_steps, "
                    "risk_summary. Ethical manual Google searches only; no scraping."
                ),
            },
            ensure_ascii=False,
        )
        response = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an ethical privacy remediation planner. Return only a JSON object. "
                        "Keep grounded_script 2-4 sentences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        updated["grounded_script"] = str(data.get("grounded_script", "")).strip()
        updated["remediation_steps"] = list(data.get("remediation_steps", []))[:4]
        updated["verification_steps"] = list(data.get("verification_steps", []))[:4]
        updated["risk_summary"] = str(data.get("risk_summary", "")).strip()
        updated["unverified"] = True
        if not updated["grounded_script"]:
            raise ValueError("grounded_script was empty")
    except Exception as exc:
        print(f"[grounding] fallback: {type(exc).__name__}: {exc}")
        updated.update(_fallback_grounding(updated))
    updated["agent_notes"] = updated.get("agent_notes", []) + [
        "Analyzer and remediation planner produced manual verification guidance."
    ]
    return updated


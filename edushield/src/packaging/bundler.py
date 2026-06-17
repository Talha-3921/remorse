import base64
import html
import mimetypes
import shutil
import zipfile
from pathlib import Path


def _data_uri(path_value: str | None, fallback_mime: str) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    mime = mimetypes.guess_type(path.name)[0] or fallback_mime
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _checklist_html(items: list[dict], prefix: str) -> str:
    rendered = []
    for idx, item in enumerate(items, start=1):
        step = html.escape(str(item.get("step", f"Step {idx}")))
        action = html.escape(str(item.get("action", "")))
        rendered.append(
            f'<label class="check"><input type="checkbox" data-group="{prefix}"> '
            f'<strong>{idx}. {step}</strong><span>{action}</span></label>'
        )
    return "\n".join(rendered)


def _findings_html(findings: list[dict]) -> str:
    if not findings:
        return "<p>No strong Google snippet/meta findings were returned. Use the dorks for manual follow-up.</p>"
    cards = []
    for finding in findings:
        title = html.escape(str(finding.get("title", "Untitled result")))
        url = html.escape(str(finding.get("url", "")))
        site = html.escape(str(finding.get("site_name", "")))
        snippet = html.escape(str(finding.get("snippet") or finding.get("meta_description") or ""))
        score = html.escape(str(finding.get("match_score", 0)))
        reason = html.escape(str(finding.get("match_reason", "")))
        terms = ", ".join(str(x) for x in finding.get("matched_context_terms", []))
        cards.append(
            f"""
            <article class="finding">
              <h4>{title}</h4>
              <p><strong>Site:</strong> {site} <strong>Match score:</strong> {score}/100</p>
              <p>{snippet}</p>
              <p><strong>Why:</strong> {reason}</p>
              <p><strong>Matched terms:</strong> {html.escape(terms or "none shown")}</p>
              <p><a href="{url}">{url}</a></p>
            </article>
            """
        )
    return "\n".join(cards)


def _policy_html(policies: list[dict]) -> str:
    if not policies:
        return "<p>No site-specific policy route found yet. Verify any match manually, then contact the site owner.</p>"
    blocks = []
    for policy in policies:
        site = html.escape(str(policy.get("site", "site owner")))
        route = html.escape(str(policy.get("removal_route", "")))
        evidence = html.escape(str(policy.get("evidence_url", "")))
        queries = "".join(
            f"<li><code>{html.escape(str(query))}</code></li>"
            for query in policy.get("policy_queries", [])
        )
        blocks.append(
            f"""
            <article class="policy">
              <h4>{site}</h4>
              <p>{route}</p>
              {'<p><strong>Evidence URL:</strong> <a href="' + evidence + '">' + evidence + '</a></p>' if evidence else ''}
              <ul>{queries}</ul>
            </article>
            """
        )
    return "\n".join(blocks)


def _search_status_html(category: dict) -> str:
    checked = html.escape(str(category.get("search_results_checked", 0)))
    errors = category.get("search_errors", [])
    if not errors:
        return f"<p class='search-ok'>Google results checked: {checked}</p>"
    rendered = "".join(f"<li>{html.escape(str(error))}</li>" for error in errors[:3])
    return (
        f"<div class='search-warn'><strong>Google Search status:</strong> "
        f"Checked {checked} results. Some searches failed. "
        f"<ul>{rendered}</ul></div>"
    )


def build_report_html(pipeline_result: dict) -> str:
    sections = []
    for idx, category in enumerate(pipeline_result.get("categories", []), start=1):
        title = html.escape(str(category.get("category_title", f"Category {idx}")))
        image_uri = _data_uri(category.get("visual_path"), "image/png")
        audio_en_uri = _data_uri(category.get("audio_en"), "audio/mpeg")
        audio_ur_uri = _data_uri(category.get("audio_ur"), "audio/mpeg")
        dorks = category.get("dorks", [])
        dork_items = "".join(f"<li><code>{html.escape(str(dork))}</code></li>" for dork in dorks)
        findings = _findings_html(category.get("findings", []))
        policies = _policy_html(category.get("site_policy_research", []))
        search_status = _search_status_html(category)
        checklist = _checklist_html(category.get("checklist", {}).get("items", []), f"cat-{idx}")
        fallback_note = (
            "<p class='note'>Urdu translation fell back to English guidance.</p>"
            if category.get("urdu_is_fallback")
            else ""
        )
        unverified = "<span class='badge'>Unverified until manually checked</span>" if category.get("unverified") else ""
        sections.append(
            f"""
            <section class="category">
              <h2>{idx}. {title} {unverified}</h2>
              {'<img src="' + image_uri + '" alt="Visual privacy guide for ' + title + '">' if image_uri else '<p>Visual unavailable.</p>'}
              <div class="audio-grid">
                <div><h3>English Instructions</h3>{'<audio controls src="' + audio_en_uri + '"></audio>' if audio_en_uri else '<p>Audio unavailable.</p>'}</div>
                <div><h3>Urdu Instructions</h3>{'<audio controls src="' + audio_ur_uri + '"></audio>' if audio_ur_uri else '<p>Audio unavailable.</p>'}{fallback_note}</div>
              </div>
              {search_status}
              <h3>Snippet/Meta Findings</h3>
              {findings}
              <h3>Site-Specific Removal Research</h3>
              {policies}
              <h3>Manual Google Dorks</h3>
              <ol>{dork_items}</ol>
              <h3>Checklist</h3>
              <div class="checks">{checklist}</div>
            </section>
            """
        )

    warning = html.escape(str(pipeline_result.get("ethical_warning", "")))
    runtime = html.escape(str(pipeline_result.get("runtime_seconds", "")))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EduShield Offline Privacy Report</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #111; background: #fff; line-height: 1.55; }}
    header {{ background: #06283D; color: #fff; padding: 32px 7vw; }}
    main {{ max-width: 1080px; margin: 0 auto; padding: 24px; }}
    h1, h2, h3 {{ letter-spacing: 0; }}
    .warning {{ border-left: 8px solid #D97706; background: #FFF7ED; padding: 16px; margin: 18px 0; }}
    .category {{ border-top: 4px solid #06283D; padding: 28px 0; }}
    img {{ width: 100%; max-width: 720px; display: block; border: 2px solid #06283D; }}
    audio {{ width: 100%; }}
    .audio-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }}
    code {{ white-space: pre-wrap; color: #06283D; font-weight: 700; }}
    .check {{ display: block; padding: 12px; border: 2px solid #BFD7EA; margin: 10px 0; }}
    .check span {{ display: block; margin-left: 28px; }}
    .finding, .policy {{ border: 2px solid #BFD7EA; padding: 14px; margin: 12px 0; overflow-wrap: anywhere; }}
    .search-warn {{ border-left: 8px solid #DC2626; background: #FEF2F2; padding: 12px; margin: 14px 0; overflow-wrap: anywhere; }}
    .search-ok {{ border-left: 8px solid #16A34A; background: #F0FDF4; padding: 12px; }}
    .badge {{ background: #FEF3C7; color: #78350F; padding: 4px 8px; font-size: 0.8em; }}
    .note {{ color: #7C2D12; font-weight: 700; }}
  </style>
</head>
<body>
  <header>
    <h1>EduShield Privacy Report</h1>
    <p>Offline guide for manual public-exposure checks and remediation.</p>
  </header>
  <main>
    <div class="warning"><strong>Ethical use:</strong> {warning}</div>
    <p><strong>Runtime:</strong> {runtime} seconds</p>
    {''.join(sections)}
  </main>
</body>
</html>"""


def bundle_offline_package(pipeline_result: dict, out_dir: str) -> str:
    """Build self-contained index.html, copy assets, zip, and return path."""
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    package_dir = output / "edushield_offline_report"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    assets_dir = package_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    for category in pipeline_result.get("categories", []):
        for key in ("visual_path", "audio_en", "audio_ur"):
            value = category.get(key)
            if value and Path(value).exists():
                shutil.copy2(value, assets_dir / Path(value).name)

    index_html = build_report_html(pipeline_result)
    (package_dir / "index.html").write_text(index_html, encoding="utf-8")
    zip_path = output / "edushield_offline_report.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in package_dir.rglob("*"):
            archive.write(file_path, file_path.relative_to(package_dir))
    return str(zip_path)

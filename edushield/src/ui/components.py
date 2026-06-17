import html

from src.packaging.bundler import build_report_html


def pipeline_to_ui_html(pipeline_result: dict) -> str:
    """Render only final per-category output for the main Gradio view."""
    return build_report_html(pipeline_result)


def trace_to_text(pipeline_result: dict) -> str:
    trace = pipeline_result.get("trace", [])
    return "\n".join(html.unescape(str(line)) for line in trace)


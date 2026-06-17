from pathlib import Path

import gradio as gr

from src.agents.orchestrator import run_pipeline
from src.config import settings
from src.packaging.bundler import bundle_offline_package
from src.ui.components import pipeline_to_ui_html, trace_to_text


def transcribe_audio(audio_path: str | None) -> str:
    if not audio_path:
        return ""
    try:
        client = settings.get_client()
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
        return getattr(transcript, "text", "") or ""
    except Exception as exc:
        print(f"[ui] voice transcription unavailable: {type(exc).__name__}: {exc}")
        return ""


def run_audit(user_text: str, audio_path: str | None):
    try:
        text = (user_text or "").strip()
        audio_text = transcribe_audio(audio_path)
        combined = "\n".join(part for part in [text, audio_text] if part.strip())
        if not combined:
            raise gr.Error("Enter your details or record a voice note first.")
        result = run_pipeline(combined)
        zip_path = bundle_offline_package(result, str(settings.OUTPUT_DIR))
        return pipeline_to_ui_html(result), zip_path, trace_to_text(result)
    except gr.Error:
        raise
    except Exception as exc:
        raise gr.Error(str(exc)) from exc


def build_app() -> gr.Blocks:
    with gr.Blocks(title="EduShield") as demo:
        with gr.Column(elem_classes=["edushield-app"]):
            gr.Markdown(
                """
                # EduShield - Protect Your Personal Data
                Privacy audit cards, audio guidance, and an offline ZIP for Pakistani university students.
                """
            )
            with gr.Row():
                user_text = gr.Textbox(
                    label="Your personal details to audit",
                    placeholder="Name, father's name, DOB, CNIC, university, student ID, email, phone...",
                    lines=8,
                )
                voice = gr.Audio(label="Optional voice input", sources=["microphone"], type="filepath")
            run_btn = gr.Button("Run Privacy Audit", variant="primary")
            report_html = gr.HTML(label="EduShield Report")
            zip_file = gr.File(label="Download Offline ZIP")
            with gr.Accordion("Agent Trace", open=False):
                trace = gr.Textbox(label="Technical trace", lines=10)
            run_btn.click(
                fn=run_audit,
                inputs=[user_text, voice],
                outputs=[report_html, zip_file, trace],
            )
    return demo


if __name__ == "__main__":
    settings.require_api_key()
    build_app().launch()

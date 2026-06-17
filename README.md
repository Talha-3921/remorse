# remorse

Hackathon project: **EduShield**, a Python/Gradio privacy-audit app for Pakistani university students.

The app lives in [`edushield/`](edushield/). It generates AI-created Google dorks at runtime, checks them through Google Custom Search JSON API, matches snippets/meta against the full user context, creates site-specific removal guidance, visual cards, English/Urdu audio, checklists, and a downloadable offline ZIP report.

## Run

```powershell
cd edushield
python -m pip install -r requirements.txt
python app.py
```

Keep your OpenAI key in `edushield/.env`. Do not commit `.env`.

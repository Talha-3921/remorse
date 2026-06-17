# remorse

Hackathon project: **EduShield**, a Python/Gradio privacy-audit app for Pakistani university students.

The app lives in [`edushield/`](edushield/). It generates ethical manual Google dorks, visual remediation cards, English/Urdu audio guidance, checklists, and a downloadable offline ZIP report.

## Run

```powershell
cd edushield
python -m pip install -r requirements.txt
python app.py
```

Keep your OpenAI key in `edushield/.env`. Do not commit `.env`.

# EduShield

EduShield is a Gradio privacy-audit app for university students in Pakistan. It turns personal details into clear exposure categories, generates ethical manual Google dorks, creates visual remediation cards, produces English and Urdu audio guidance, and exports a fully offline ZIP report.

## Run

```powershell
cd edushield
python -m pip install -r requirements.txt
copy .env.example .env
```

Put your OpenAI key in `.env`, then:

```powershell
python app.py
```

Open the local Gradio URL printed in the terminal.

## Safety

EduShield is for checking your own public exposure and requesting legitimate remediation. It does not scrape websites, bypass access controls, or automate searches. All dorks are meant to be pasted manually into Google by the user.


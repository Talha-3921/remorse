# EduShield

EduShield is a Gradio privacy-audit app for university students in Pakistan. It turns personal details into clear exposure categories, generates ethical manual Google dorks, creates visual remediation cards, produces English and Urdu audio guidance, and exports a fully offline ZIP report.

## Run

```powershell
cd edushield
python -m pip install -r requirements.txt
copy .env.example .env
```

Put your OpenAI key and Google Custom Search values in `.env`, then:

```powershell
python app.py
```

Open the local Gradio URL printed in the terminal.

## Required Search Setup

EduShield uses Google's official Custom Search JSON API for live dork checks. Add:

```env
GOOGLE_API_KEY=your-google-custom-search-api-key
GOOGLE_CSE_ID=your-programmable-search-engine-id
```

If these are missing, the app will still generate dorks and guidance, but it will clearly mark live search as unavailable.

If you see `This project does not have the access to Custom Search JSON API`, enable **Custom Search JSON API** in the same Google Cloud project that owns your API key, then restart the app.

## Safety

EduShield is for checking your own public exposure and requesting legitimate remediation. It uses the official Google Custom Search JSON API, does not scrape Google result pages, and does not bypass access controls.

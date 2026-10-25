# Calmind AI — Your Mindful AI Companion

A responsive Flask starter app for mood check-ins, journaling, supportive Gemini-powered chat, basic TextBlob sentiment analysis, and CSV export for Orange Data Mining.

## Features
- Account registration and login with hashed passwords
- MongoDB persistence for users, moods, journals, and chat history
- Gemini-powered companion when a valid API key is configured
- TextBlob sentiment estimate for journal entries
- Seven-day dashboard summary and CSV export
- Midnight navy UI with warm orange accents

## Run locally (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
python -m textblob.download_corpora
python app.py
```
Edit `.env` with a strong `SECRET_KEY`, your MongoDB connection string in `MONGO_URI`, and optional `GEMINI_API_KEY`. Then open http://127.0.0.1:5000.

## Deploy on Render
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`
- Add `SECRET_KEY`, `MONGO_URI`, `GEMINI_API_KEY`, `GEMINI_MODEL`, and `FLASK_DEBUG=false` in the host's environment settings.
- Use MongoDB Atlas or another reachable MongoDB deployment; configure its network access securely.

## Orange Data Mining
Use the **Export CSV** link after signing in. In Orange, load the downloaded `calmind-moods.csv` with the **File** widget and connect it to **Data Table**, **Distributions**, or other analysis widgets.

## Important
This is an educational starter, not a clinical tool or substitute for mental-health care. TextBlob sentiment is approximate. Before public use, add CSRF protection, rate limiting, stronger session settings, input validation, monitoring, and backups. Set a unique secret in production; never commit `.env` or API keys. Password reset, email verification, account deletion, and MFA are not included.

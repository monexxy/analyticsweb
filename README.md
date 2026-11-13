# UPGRADE ANALYTICS

Responsive web version of the historical results tracker. Works on desktop and mobile browsers.

## Features
- Responsive analysis dashboard
- Manual recording of already completed outcomes
- Historical summary and descriptive statistics
- Calculation history
- Methodology explanations
- SQLite storage for local/self-hosted use

This application does not connect to game services, initiate attempts, or predict the next independent random outcome. It is a historical record and descriptive statistics tool.

## Run locally

Python 3.10+

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000

## Deploy on Render

1. Push this folder to a GitHub repository.
2. In Render choose **New + → Web Service** and connect the repository.
3. Runtime: **Python 3**.
4. Build command: `pip install -r requirements.txt`
5. Start command: `gunicorn app:app`
6. Deploy.

## Storage note

The included SQLite database is created automatically. On hosting platforms with an ephemeral filesystem, SQLite data may be lost when the service is replaced or restarted. For durable multi-user production storage, connect a managed PostgreSQL database and migrate the database layer before relying on it for long-term records.

## Project structure

- `app.py` — Flask routes and API
- `analysis_engine.py` — shared calculation engine
- `database.py` — SQLite persistence
- `templates/index.html` — responsive app interface
- `static/style.css` — red/yellow responsive design
- `static/app.js` — frontend interactions

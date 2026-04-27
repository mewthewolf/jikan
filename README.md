# Jikan

Jikan is a local-only macOS productivity system that turns ActivityWatch data into structured work session reports.

## Components

- `backend/`: FastAPI service for session control, ActivityWatch ingestion, classification, persistence, and report generation.
- `desktop/`: Tauri desktop app that starts/stops sessions and previews the latest report.

## Requirements

- macOS with ActivityWatch installed and running on `http://localhost:5600`
- Python 3.14+
- Rust + Cargo
- Node.js + npm
- `OPENAI_API_KEY` in `.env`

## Backend quick start

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp ../.env.example .env
uvicorn app.main:app --reload
```

## Desktop app quick start

```bash
cd desktop
npm install
npm run tauri:dev
```

## Notes

- ActivityWatch remains an external dependency.
- Reports are written to `backend/reports/`.
- If `OPENAI_API_KEY` is unset, the backend falls back to a deterministic Markdown report instead of calling OpenAI.
- The desktop app expects the backend to be running on `http://127.0.0.1:8000` unless you override it.

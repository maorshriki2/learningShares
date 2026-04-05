# learningShares

FastAPI + Streamlit platform for market education: real-time charts, fundamentals, SEC governance, FinBERT sentiment, and paper trading.

## Quick start

1. Copy `.env.example` to `.env` and set `SEC_USER_AGENT` (required for SEC) and optional API keys.
2. Start Redis: `docker compose up -d`
3. Install: `pip install -e ".[dev]"`
4. Run app (API + Streamlit in one process): `python scripts/run_app.py`

Open the URL printed as `learningShares UI` (default `http://127.0.0.1:8501`). The API is started automatically on `API_PORT` (default `8000`).

## Windows desktop build (optional)

- One-file EXE: `python -m PyInstaller --noconfirm learningSharesDesktop.spec` → `dist/learningSharesDesktop.exe`
- Installer (Inno Setup): `.\scripts\build_windows_installer.ps1` → `installer_output/learningShares-Setup-0.1.0.exe`

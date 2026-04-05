"""Single entry: FastAPI + Streamlit together (local development).

Run from project root:
    python scripts/run_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_scripts = Path(__file__).resolve().parent
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))

import desktop_launcher  # noqa: E402

if __name__ == "__main__":
    desktop_launcher.cli_main(pause_on_error=False)

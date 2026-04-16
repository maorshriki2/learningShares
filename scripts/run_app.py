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

try:
    import desktop_launcher  # noqa: E402
except ModuleNotFoundError as e:  # pragma: no cover
    # Common dev pitfall on Windows: running system Python instead of the project's .venv.
    missing = getattr(e, "name", None) or ""
    if missing == "uvicorn":
        venv_python = Path(__file__).resolve().parents[1] / ".venv" / "Scripts" / "python.exe"
        print(
            "\nMissing dependency: uvicorn\n"
            "It looks like you're running a Python interpreter outside the project's .venv.\n\n"
            "Fix (PowerShell, from repo root):\n"
            f'  & "{venv_python}" scripts\\run_app.py\n\n'
            "Or activate the venv first:\n"
            "  .\\.venv\\Scripts\\Activate.ps1\n"
            "  python scripts\\run_app.py\n",
            file=sys.stderr,
            flush=True,
        )
        raise SystemExit(1) from None
    raise

if __name__ == "__main__":
    desktop_launcher.cli_main(pause_on_error=False)

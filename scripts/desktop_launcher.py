from __future__ import annotations

import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from pathlib import Path

import httpx
import uvicorn


def _bundle_root() -> Path:
    """Read-only extracted bundle (PyInstaller _MEIPASS) or project root in dev."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


def _install_dir() -> Path:
    """Folder next to the .exe (frozen) or project root (dev) — writable logs & user data."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _apply_user_dotenv(path: Path) -> None:
    """Load KEY=VAL from a .env file into os.environ (no extra deps)."""
    if not path.is_file():
        return
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError:
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        os.environ[key] = val


def _wait_for_api(base_url: str, timeout_s: float = 25.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{base_url}/api/v1/health", timeout=2.0)
            if resp.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.4)
    return False


def _api_health_ok(base_url: str) -> bool:
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/api/v1/health", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def _openapi_has_path(base_url: str, path: str) -> bool:
    """True if OpenAPI lists `path` (e.g. /api/v1/blindtest/analyze-scenario)."""
    try:
        r = httpx.get(f"{base_url.rstrip('/')}/openapi.json", timeout=2.5)
        if r.status_code != 200:
            return False
        paths = r.json().get("paths") or {}
        return path in paths
    except Exception:
        return False


def _tcp_port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


def _pick_api_port(host: str, preferred: int, span: int = 32) -> int:
    """Prefer `preferred`; if taken, use the next free port in range."""
    for port in range(preferred, preferred + span):
        if _tcp_port_is_free(host, port):
            return port
    raise RuntimeError(
        f"No free TCP port for API in range {preferred}-{preferred + span - 1} on {host}. "
        "Close other apps using those ports or change API_PORT in .env."
    )


def _pick_streamlit_port(host: str, preferred: int, span: int = 40) -> int:
    """First free port from `preferred` so the browser URL matches Streamlit (no silent +1/+2)."""
    for port in range(preferred, preferred + span):
        if _tcp_port_is_free(host, port):
            return port
    raise RuntimeError(
        f"No free TCP port for Streamlit in range {preferred}-{preferred + span - 1} on {host}. "
        "Close other Streamlit/python processes or change STREAMLIT_SERVER_PORT in .env."
    )


def main() -> None:
    bundle = _bundle_root()
    install = _install_dir()
    src_dir = bundle / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    if getattr(sys, "frozen", False):
        _apply_user_dotenv(install / ".env")
        data_dir = install / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("PORTFOLIO_STORAGE_PATH", str(data_dir / "portfolio.json"))

    os.chdir(bundle)

    from market_intel.config.settings import get_settings
    from streamlit.web import bootstrap

    get_settings.cache_clear()
    settings = get_settings()
    streamlit_host = "127.0.0.1"
    preferred_ui_port = int(settings.streamlit_server_port)
    streamlit_port = _pick_streamlit_port(streamlit_host, preferred_ui_port)

    api_host = "127.0.0.1"
    preferred_api_port = int(settings.api_port)
    app_path = str(src_dir / "market_intel" / "ui" / "app.py")

    # Reuse an existing API only if it is healthy *and* exposes current routes (avoid stale uvicorn).
    required_route = "/api/v1/blindtest/analyze-scenario"
    api_base = f"http://{api_host}:{preferred_api_port}"
    own_api_server = True
    if _api_health_ok(api_base) and _openapi_has_path(api_base, required_route):
        own_api_server = False
    else:
        api_port = _pick_api_port(api_host, preferred_api_port)
        api_base = f"http://{api_host}:{api_port}"
        os.environ["API_PORT"] = str(api_port)
        os.environ["API_PUBLIC_URL"] = api_base
        get_settings.cache_clear()
        config = uvicorn.Config(
            "market_intel.api.main:app", host=api_host, port=api_port, log_level="info"
        )
        server = uvicorn.Server(config)
        t = threading.Thread(target=server.run, daemon=True)
        t.start()
        if not _wait_for_api(api_base):
            server.should_exit = True
            t.join(timeout=5.0)
            raise RuntimeError("API server did not start in time.")

    os.environ["API_PUBLIC_URL"] = api_base

    # Match Streamlit CLI: keys use underscores instead of dots (see streamlit web/cli.py).
    # bootstrap.run() does NOT apply flag_options until load_config_options() — without this call,
    # Streamlit uses defaults, opens localhost, and webbrowser.open(127.0.0.1) → two tabs.
    streamlit_flag_options = {
        "global_developmentMode": False,
        "server_address": streamlit_host,
        "server_port": streamlit_port,
        "server_headless": True,
        "server_enableXsrfProtection": False,
        "server_enableCORS": False,
        "browser_serverAddress": streamlit_host,
        "browser_serverPort": streamlit_port,
    }
    bootstrap.load_config_options(streamlit_flag_options)

    ui_url = f"http://{streamlit_host}:{streamlit_port}"
    print(f"\nlearningShares UI: {ui_url}\nAPI: {api_base}\n", flush=True)
    webbrowser.open(ui_url)
    try:
        bootstrap.run(app_path, False, [], streamlit_flag_options)
    finally:
        if own_api_server:
            server.should_exit = True
            t.join(timeout=5.0)


def cli_main(*, pause_on_error: bool | None = None) -> None:
    """Entry point for EXE and for `python scripts/run_app.py`."""
    if pause_on_error is None:
        pause_on_error = bool(getattr(sys, "frozen", False))

    if getattr(sys, "frozen", False):
        import multiprocessing

        multiprocessing.freeze_support()
    try:
        main()
    except Exception:
        log_path = (
            _install_dir() / "learningSharesDesktop_error.log"
            if getattr(sys, "frozen", False)
            else _bundle_root() / "learningSharesDesktop_error.log"
        )
        err = f"{traceback.format_exc()}"
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        print("learningShares failed to start.")
        print(err)
        print(f"\nError log saved to: {log_path}")
        if pause_on_error:
            input("\nPress Enter to close...")
        raise SystemExit(1) from None


if __name__ == "__main__":
    cli_main()

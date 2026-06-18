from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path

from simple_terminal.simple_api import SimpleTerminalAPI


LOG_DIR = Path.home() / ".simple_persian_powershell"
LOG_FILE = LOG_DIR / "debug.log"


def log(message: str) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass


def app_root() -> Path:
    # PyInstaller extracts bundled files to sys._MEIPASS.
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "simple_terminal"
    return Path(__file__).resolve().parent


def main() -> None:
    try:
        root = app_root()
        frontend = root / "web" / "index.html"
        log(f"starting; frozen={getattr(sys, 'frozen', False)}; root={root}; frontend={frontend}; exists={frontend.exists()}")

        try:
            import webview
        except ImportError as exc:  # pragma: no cover
            log("pywebview import failed:\n" + traceback.format_exc())
            raise SystemExit("pywebview is not installed. Run: pip install -r requirements.txt") from exc

        if not frontend.exists():
            raise FileNotFoundError(f"Frontend file not found: {frontend}")

        api = SimpleTerminalAPI()
        webview.create_window(
            "Simple Persian PowerShell",
            frontend.as_uri(),
            js_api=api,
            width=1100,
            height=700,
            min_size=(760, 420),
            text_select=True,
        )
        log("window created")
        webview.start(debug=False)
        log("webview stopped")
    except Exception:
        log("fatal error:\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()

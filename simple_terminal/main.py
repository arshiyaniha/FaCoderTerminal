from __future__ import annotations

from pathlib import Path

from .simple_api import SimpleTerminalAPI


def main() -> None:
    root = Path(__file__).resolve().parent
    frontend = root / "web" / "index.html"

    try:
        import webview
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("pywebview is not installed. Run: pip install -r requirements.txt") from exc

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
    webview.start(debug=False)


if __name__ == "__main__":
    main()

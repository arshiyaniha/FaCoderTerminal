from __future__ import annotations

from pathlib import Path

from .api import AppAPI


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    frontend_file = project_root / "frontend" / "index.html"

    try:
        import webview
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "pywebview نصب نیست. ابتدا دستور زیر را اجرا کنید: pip install -r requirements.txt"
        ) from exc

    api = AppAPI(project_root)
    webview.create_window(
        "FaCoderTerminal",
        frontend_file.as_uri(),
        js_api=api,
        width=1220,
        height=760,
        min_size=(960, 620),
        text_select=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from .api import AppAPI
from .temp_logger import logger


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    frontend_file = project_root / "frontend" / "index.html"
    logger.log("info", "main", "application starting", {"project_root": str(project_root), "frontend": str(frontend_file)})

    try:
        import webview
    except ImportError as exc:  # pragma: no cover
        logger.exception("main.import_webview", exc)
        raise SystemExit(
            "pywebview نصب نیست. ابتدا دستور زیر را اجرا کنید: pip install -r requirements.txt"
        ) from exc

    try:
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
        logger.log("info", "main", "webview window created")
        webview.start(debug=False)
        logger.log("info", "main", "webview stopped")
    except Exception as exc:
        logger.exception("main", exc)
        raise


if __name__ == "__main__":
    main()

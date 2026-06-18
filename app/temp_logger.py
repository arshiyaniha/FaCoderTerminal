from __future__ import annotations

import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TempLogger:
    def __init__(self) -> None:
        self.root = Path.home() / ".facoderterminal" / "logs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "debug.log"

    def log(self, level: str, area: str, message: str, data: dict[str, Any] | None = None) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "area": area,
            "message": message,
            "data": data or {},
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def exception(self, area: str, exc: BaseException, data: dict[str, Any] | None = None) -> None:
        payload = dict(data or {})
        payload["exception_type"] = type(exc).__name__
        payload["traceback"] = traceback.format_exc()
        self.log("error", area, str(exc), payload)

    def tail(self, lines: int = 120) -> str:
        if not self.path.exists():
            return ""
        try:
            content = self.path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(content[-lines:])
        except OSError as exc:
            return f"Could not read log: {exc}"


logger = TempLogger()

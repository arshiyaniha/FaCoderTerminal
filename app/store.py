from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import AppSettings, HistoryItem


class JsonStore:
    def __init__(self) -> None:
        self.root = Path.home() / ".facoderterminal"
        self.root.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.root / "settings.json"
        self.history_path = self.root / "history.json"

    def load_settings(self) -> AppSettings:
        if not self.settings_path.exists():
            return AppSettings()
        try:
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            return AppSettings.model_validate(data)
        except (json.JSONDecodeError, ValidationError, OSError):
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        self.settings_path.write_text(
            json.dumps(settings.model_dump(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load_history(self) -> list[HistoryItem]:
        if not self.history_path.exists():
            return []
        try:
            raw = json.loads(self.history_path.read_text(encoding="utf-8"))
            return [HistoryItem.model_validate(item) for item in raw[-200:]]
        except (json.JSONDecodeError, ValidationError, OSError):
            return []

    def append_history(self, item: HistoryItem) -> None:
        history = self.load_history()
        history.append(item)
        history = history[-200:]
        self.history_path.write_text(
            json.dumps([entry.model_dump() for entry in history], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def mask_key(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "********"
        return f"{value[:3]}********{value[-4:]}"

    def public_settings(self, settings: AppSettings) -> dict[str, Any]:
        data = settings.model_dump()
        data["llm"]["api_key"] = self.mask_key(settings.llm.api_key)
        return data

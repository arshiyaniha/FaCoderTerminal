from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from .models import CatalogCommand


class CatalogError(Exception):
    pass


class CommandCatalog:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.commands: dict[str, CatalogCommand] = {}

    def load(self) -> None:
        kb_dir = self.root / "knowledge_base"
        if not kb_dir.exists():
            raise CatalogError("پوشه Knowledge Base پیدا نشد.")

        loaded: dict[str, CatalogCommand] = {}
        errors: list[str] = []
        for file_path in sorted(kb_dir.glob("commands.*.json")):
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                for item in payload.get("commands", []):
                    command = CatalogCommand.model_validate(item)
                    if command.id in loaded:
                        errors.append(f"شناسه تکراری: {command.id}")
                    loaded[command.id] = command
            except (json.JSONDecodeError, ValidationError, OSError) as exc:
                errors.append(f"{file_path.name}: {exc}")

        if errors:
            raise CatalogError("\n".join(errors))
        self.commands = loaded

    def get(self, command_id: str) -> CatalogCommand | None:
        return self.commands.get(command_id)

    def all(self) -> list[CatalogCommand]:
        return sorted(self.commands.values(), key=lambda item: item.id)

    def public_list(self) -> list[dict[str, object]]:
        return [
            {
                "id": command.id,
                "tool": command.tool,
                "title_fa": command.title_fa,
                "description_fa": command.description_fa,
                "risk": command.risk.value,
                "requires_confirmation": command.requires_confirmation,
                "category": command.category,
                "aliases_fa": command.aliases_fa,
            }
            for command in self.all()
        ]

    def candidates_for_prompt(self, limit: int = 40) -> list[dict[str, object]]:
        return [
            {
                "id": command.id,
                "tool": command.tool,
                "title_fa": command.title_fa,
                "description_fa": command.description_fa,
                "aliases_fa": command.aliases_fa[:8],
                "risk": command.risk.value,
            }
            for command in self.all()[:limit]
        ]

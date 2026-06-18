from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .ai_client import LLMClient, LLMClientError
from .catalog import CatalogError, CommandCatalog
from .matcher import LocalMatcher
from .models import AppSettings, HistoryItem
from .normalizer import normalize_fa
from .project_sync import ProjectSyncService
from .pty_session import EmbeddedSession
from .runner import CommandRenderError, CommandRunner
from .store import JsonStore


class AppAPI:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.store = JsonStore()
        self.settings = self.store.load_settings()
        self.catalog = CommandCatalog(project_root)
        try:
            self.catalog.load()
            self.catalog_error = ""
        except CatalogError as exc:
            self.catalog_error = str(exc)
        self.runner = CommandRunner(project_root, self.settings.default_timeout_seconds)
        self.live = EmbeddedSession()

    def get_bootstrap(self) -> dict[str, Any]:
        return {"ok": not bool(self.catalog_error), "catalog_error": self.catalog_error, "settings": self.store.public_settings(self.settings), "commands": self.catalog.public_list() if not self.catalog_error else [], "history": [item.model_dump(mode="json") for item in self.store.load_history()], "project_root": str(self.project_root)}

    def sync_health(self) -> dict[str, Any]:
        return ProjectSyncService(self.settings, self.project_root).health()

    def make_keypair(self) -> dict[str, Any]:
        return ProjectSyncService(self.settings, self.project_root).generate_keypair()

    def server_run(self, command_text: str) -> dict[str, Any]:
        return ProjectSyncService(self.settings, self.project_root).server_exec(command_text)

    def live_start(self, project_path: str = "") -> dict[str, Any]:
        cwd = project_path or self.settings.default_project_path or str(self.project_root)
        return self.live.start(cwd)

    def live_send(self, text: str) -> dict[str, Any]:
        return self.live.write(text)

    def live_resize(self, cols: int, rows: int) -> dict[str, Any]:
        return self.live.resize(cols, rows)

    def live_read(self) -> dict[str, Any]:
        return self.live.read()

    def live_stop(self) -> dict[str, Any]:
        return self.live.stop()

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        current_key = self.settings.llm.api_key
        incoming = payload or {}
        llm_payload = incoming.get("llm", {})
        api_key = str(llm_payload.get("api_key", "")).strip()
        if "********" in api_key:
            llm_payload["api_key"] = current_key
        else:
            llm_payload["api_key"] = api_key
        incoming["llm"] = llm_payload
        self.settings = AppSettings.model_validate(incoming)
        self.store.save_settings(self.settings)
        self.runner = CommandRunner(self.project_root, self.settings.default_timeout_seconds)
        return {"ok": True, "settings": self.store.public_settings(self.settings)}

    def test_llm(self) -> dict[str, Any]:
        return LLMClient(self.settings.llm).test_connection()

    def parse_request(self, text: str, project_path: str = "") -> dict[str, Any]:
        if self.catalog_error:
            return {"ok": False, "message_fa": self.catalog_error}
        normalized = normalize_fa(text)
        matcher = LocalMatcher(self.catalog.all())
        intent = matcher.match(normalized)
        if intent is None:
            try:
                client = LLMClient(self.settings.llm)
                intent = client.parse_intent(normalized, self.catalog.candidates_for_prompt())
            except LLMClientError as exc:
                return {"ok": False, "message_fa": str(exc), "needs_settings": True}
        if intent.needs_clarification:
            return {"ok": False, "needs_clarification": True, "message_fa": intent.explanation_fa or "درخواست مبهم است."}
        command = self.catalog.get(intent.command_id)
        if command is None:
            return {"ok": False, "message_fa": "مدل یا matcher دستور معتبری انتخاب نکرد."}
        try:
            plan = self.runner.build_plan(command=command, args=intent.args, project_path=project_path or self.settings.default_project_path, explanation_fa=intent.explanation_fa)
        except CommandRenderError as exc:
            return {"ok": False, "message_fa": str(exc)}
        return {"ok": True, "intent": intent.model_dump(mode="json"), "plan": plan.model_dump(mode="json"), "command_preview": " ".join(plan.argv)}

    def run_command(self, command_id: str, args: dict[str, Any] | None = None, project_path: str = "", confirmed: bool = False, user_text: str = "") -> dict[str, Any]:
        if self.catalog_error:
            return {"ok": False, "message_fa": self.catalog_error}
        command = self.catalog.get(command_id)
        if command is None:
            return {"ok": False, "message_fa": "شناسه دستور در catalog وجود ندارد."}
        try:
            plan = self.runner.build_plan(command, args or {}, project_path or self.settings.default_project_path)
        except CommandRenderError as exc:
            return {"ok": False, "message_fa": str(exc)}
        result = self.runner.run(plan, confirmed=confirmed)
        if self.settings.save_history:
            preview = (result.stdout or result.stderr or result.message_fa)[:1000]
            self.store.append_history(HistoryItem(timestamp=datetime.now(timezone.utc).isoformat(), user_text=user_text, command_id=command.id, title_fa=command.title_fa, risk=command.risk, project_path=plan.project_path, ok=result.ok, exit_code=result.exit_code, output_preview=preview))
        return {"ok": result.ok, "plan": plan.model_dump(mode="json"), "result": result.model_dump(mode="json")}

    def get_history(self) -> dict[str, Any]:
        return {"ok": True, "history": [item.model_dump(mode="json") for item in self.store.load_history()]}

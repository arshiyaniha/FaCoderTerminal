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
from .temp_logger import logger


class AppAPI:
    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        logger.log("info", "api.init", "AppAPI init started", {"project_root": str(project_root)})
        try:
            self.store = JsonStore()
            self.settings = self.store.load_settings()
            self.catalog = CommandCatalog(project_root)
            try:
                self.catalog.load()
                self.catalog_error = ""
                logger.log("info", "catalog", "catalog loaded", {"commands": len(self.catalog.all())})
            except CatalogError as exc:
                self.catalog_error = str(exc)
                logger.exception("catalog", exc)
            self.runner = CommandRunner(project_root, self.settings.default_timeout_seconds)
            self.live = EmbeddedSession()
            logger.log("info", "api.init", "AppAPI init finished")
        except Exception as exc:
            logger.exception("api.init", exc)
            raise

    def temp_log(self, level: str, area: str, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        logger.log(level or "info", area or "ui", message or "", data or {})
        return {"ok": True, "log_path": str(logger.path)}

    def get_temp_log(self) -> dict[str, Any]:
        return {"ok": True, "log_path": str(logger.path), "content": logger.tail()}

    def get_bootstrap(self) -> dict[str, Any]:
        logger.log("info", "api.bootstrap", "bootstrap requested")
        return {"ok": not bool(self.catalog_error), "catalog_error": self.catalog_error, "settings": self.store.public_settings(self.settings), "commands": self.catalog.public_list() if not self.catalog_error else [], "history": [item.model_dump(mode="json") for item in self.store.load_history()], "project_root": str(self.project_root), "log_path": str(logger.path)}

    def sync_health(self) -> dict[str, Any]:
        try:
            return ProjectSyncService(self.settings, self.project_root).health()
        except Exception as exc:
            logger.exception("sync.health", exc)
            return {"ok": False, "message_fa": str(exc)}

    def make_keypair(self) -> dict[str, Any]:
        try:
            return ProjectSyncService(self.settings, self.project_root).generate_keypair()
        except Exception as exc:
            logger.exception("server.keypair", exc)
            return {"ok": False, "message_fa": str(exc)}

    def server_run(self, command_text: str) -> dict[str, Any]:
        try:
            return ProjectSyncService(self.settings, self.project_root).server_exec(command_text)
        except Exception as exc:
            logger.exception("server.run", exc, {"command_text": command_text})
            return {"ok": False, "message_fa": str(exc)}

    def live_start(self, project_path: str = "") -> dict[str, Any]:
        cwd = project_path or self.settings.default_project_path or str(self.project_root)
        logger.log("info", "live.start", "starting embedded session", {"cwd": cwd})
        result = self.live.start(cwd)
        logger.log("info" if result.get("ok") else "error", "live.start", "embedded session start result", result)
        return result

    def live_send(self, text: str) -> dict[str, Any]:
        try:
            return self.live.write(text)
        except Exception as exc:
            logger.exception("live.send", exc)
            return {"ok": False, "message_fa": str(exc)}

    def live_resize(self, cols: int, rows: int) -> dict[str, Any]:
        try:
            return self.live.resize(cols, rows)
        except Exception as exc:
            logger.exception("live.resize", exc, {"cols": cols, "rows": rows})
            return {"ok": False, "message_fa": str(exc)}

    def live_read(self) -> dict[str, Any]:
        try:
            return self.live.read()
        except Exception as exc:
            logger.exception("live.read", exc)
            return {"ok": False, "message_fa": str(exc), "output": ""}

    def live_stop(self) -> dict[str, Any]:
        try:
            return self.live.stop()
        except Exception as exc:
            logger.exception("live.stop", exc)
            return {"ok": False, "message_fa": str(exc)}

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
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
            logger.log("info", "settings", "settings saved", {"project_path": self.settings.default_project_path, "server_host": self.settings.server.host})
            return {"ok": True, "settings": self.store.public_settings(self.settings)}
        except Exception as exc:
            logger.exception("settings.save", exc)
            return {"ok": False, "message_fa": str(exc)}

    def test_llm(self) -> dict[str, Any]:
        result = LLMClient(self.settings.llm).test_connection()
        logger.log("info" if result.get("ok") else "error", "llm.test", "test llm result", result)
        return result

    def parse_request(self, text: str, project_path: str = "") -> dict[str, Any]:
        try:
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
                    logger.exception("llm.parse", exc, {"text": text})
                    return {"ok": False, "message_fa": str(exc), "needs_settings": True}
            if intent.needs_clarification:
                return {"ok": False, "needs_clarification": True, "message_fa": intent.explanation_fa or "درخواست مبهم است."}
            command = self.catalog.get(intent.command_id)
            if command is None:
                return {"ok": False, "message_fa": "مدل یا matcher دستور معتبری انتخاب نکرد."}
            try:
                plan = self.runner.build_plan(command=command, args=intent.args, project_path=project_path or self.settings.default_project_path, explanation_fa=intent.explanation_fa)
            except CommandRenderError as exc:
                logger.exception("command.plan", exc, {"command_id": intent.command_id})
                return {"ok": False, "message_fa": str(exc)}
            logger.log("info", "parse", "parse request ok", {"command_id": intent.command_id, "source": intent.source})
            return {"ok": True, "intent": intent.model_dump(mode="json"), "plan": plan.model_dump(mode="json"), "command_preview": " ".join(plan.argv)}
        except Exception as exc:
            logger.exception("parse", exc, {"text": text})
            return {"ok": False, "message_fa": str(exc)}

    def run_command(self, command_id: str, args: dict[str, Any] | None = None, project_path: str = "", confirmed: bool = False, user_text: str = "") -> dict[str, Any]:
        try:
            if self.catalog_error:
                return {"ok": False, "message_fa": self.catalog_error}
            command = self.catalog.get(command_id)
            if command is None:
                return {"ok": False, "message_fa": "شناسه دستور در catalog وجود ندارد."}
            try:
                plan = self.runner.build_plan(command, args or {}, project_path or self.settings.default_project_path)
            except CommandRenderError as exc:
                logger.exception("command.run.plan", exc, {"command_id": command_id})
                return {"ok": False, "message_fa": str(exc)}
            result = self.runner.run(plan, confirmed=confirmed)
            if self.settings.save_history:
                preview = (result.stdout or result.stderr or result.message_fa)[:1000]
                self.store.append_history(HistoryItem(timestamp=datetime.now(timezone.utc).isoformat(), user_text=user_text, command_id=command.id, title_fa=command.title_fa, risk=command.risk, project_path=plan.project_path, ok=result.ok, exit_code=result.exit_code, output_preview=preview))
            logger.log("info" if result.ok else "error", "command.run", "command run result", {"command_id": command_id, "ok": result.ok})
            return {"ok": result.ok, "plan": plan.model_dump(mode="json"), "result": result.model_dump(mode="json")}
        except Exception as exc:
            logger.exception("command.run", exc, {"command_id": command_id})
            return {"ok": False, "message_fa": str(exc)}

    def get_history(self) -> dict[str, Any]:
        return {"ok": True, "history": [item.model_dump(mode="json") for item in self.store.load_history()]}

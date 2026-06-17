from __future__ import annotations

import re
import subprocess
import time
from pathlib import Path
from typing import Any

from .models import CatalogCommand, ExecutionPlan, RunResult
from .security import SecurityEngine


class CommandRenderError(Exception):
    pass


class CommandRunner:
    def __init__(self, project_root: Path, timeout_seconds: int = 120) -> None:
        self.project_root = project_root
        self.timeout_seconds = timeout_seconds
        self.security = SecurityEngine()

    def build_plan(
        self,
        command: CatalogCommand,
        args: dict[str, Any] | None = None,
        project_path: str = "",
        explanation_fa: str = "",
    ) -> ExecutionPlan:
        argv = self._render_argv(command, args or {})
        decision = self.security.evaluate(command)
        cwd = self._safe_cwd(project_path)
        return ExecutionPlan(
            command_id=command.id,
            title_fa=command.title_fa,
            description_fa=command.description_fa,
            argv=argv,
            risk=command.risk,
            requires_confirmation=decision.requires_confirmation,
            explanation_fa=explanation_fa or decision.message_fa,
            project_path=str(cwd),
        )

    def run(self, plan: ExecutionPlan, confirmed: bool = False) -> RunResult:
        if plan.requires_confirmation and not confirmed:
            return RunResult(
                ok=False,
                command_id=plan.command_id,
                message_fa="این عملیات نیازمند تأیید کاربر است.",
            )

        start = time.perf_counter()
        try:
            completed = subprocess.run(
                plan.argv,
                cwd=plan.project_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                shell=False,
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            return RunResult(
                ok=completed.returncode == 0,
                command_id=plan.command_id,
                stdout=completed.stdout[-20000:],
                stderr=completed.stderr[-12000:],
                exit_code=completed.returncode,
                duration_ms=duration_ms,
                message_fa="اجرا انجام شد." if completed.returncode == 0 else "اجرا با خطا تمام شد.",
            )
        except subprocess.TimeoutExpired:
            return RunResult(
                ok=False,
                command_id=plan.command_id,
                message_fa="اجرای دستور بیش از حد مجاز طول کشید و متوقف شد.",
            )
        except FileNotFoundError:
            return RunResult(
                ok=False,
                command_id=plan.command_id,
                message_fa="ابزار مورد نیاز روی سیستم پیدا نشد یا در PATH قرار ندارد.",
            )
        except OSError as exc:
            return RunResult(
                ok=False,
                command_id=plan.command_id,
                message_fa=f"خطای سیستم هنگام اجرا: {exc}",
            )

    def _safe_cwd(self, project_path: str) -> Path:
        if project_path:
            candidate = Path(project_path).expanduser()
            if candidate.exists() and candidate.is_dir():
                return candidate
        return self.project_root

    def _render_argv(self, command: CatalogCommand, args: dict[str, Any]) -> list[str]:
        values: dict[str, str] = {}
        for spec in command.args:
            raw_value = args.get(spec.name, spec.default)
            if raw_value is None and spec.required:
                raise CommandRenderError(f"آرگومان الزامی وارد نشده است: {spec.name}")
            if raw_value is None:
                values[spec.name] = ""
                continue
            value = str(raw_value)
            if spec.pattern and not re.fullmatch(spec.pattern, value):
                raise CommandRenderError(f"آرگومان معتبر نیست: {spec.name}")
            values[spec.name] = value

        rendered: list[str] = []
        for part in command.argv_template:
            rendered_part = part
            for key, value in values.items():
                rendered_part = rendered_part.replace("{{" + key + "}}", value)
            if "{{" in rendered_part or "}}" in rendered_part:
                raise CommandRenderError("command template شامل placeholder نامعتبر است.")
            rendered.append(rendered_part)
        return rendered

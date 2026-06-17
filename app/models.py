from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RiskLevel(StrEnum):
    SAFE = "safe"
    MEDIUM = "medium"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class RunMode(StrEnum):
    CAPTURED = "captured"
    NEW_WINDOW = "new_window"


class LLMSettings(BaseModel):
    provider_type: str = "openai_compatible"
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 700
    timeout_seconds: int = 30
    enabled: bool = False

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        return max(0.0, min(2.0, value))


class AppSettings(BaseModel):
    llm: LLMSettings = Field(default_factory=LLMSettings)
    default_project_path: str = ""
    font_family: str = "Vazirmatn, Segoe UI, Tahoma, sans-serif"
    terminal_font_family: str = "Cascadia Mono, Consolas, monospace"
    default_timeout_seconds: int = 120
    save_history: bool = True


class CommandArg(BaseModel):
    name: str
    required: bool = False
    default: str | None = None
    description_fa: str = ""
    pattern: str | None = None


class CatalogCommand(BaseModel):
    id: str
    tool: str
    title_fa: str
    description_fa: str
    aliases_fa: list[str] = Field(default_factory=list)
    argv_template: list[str]
    risk: RiskLevel = RiskLevel.SAFE
    requires_confirmation: bool = False
    run_mode: RunMode = RunMode.CAPTURED
    category: str = "general"
    platforms: list[str] = Field(default_factory=lambda: ["windows"])
    args: list[CommandArg] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def validate_command_id(cls, value: str) -> str:
        if "." not in value:
            raise ValueError("command id must use tool.action format")
        return value


class IntentResult(BaseModel):
    type: Literal["command_intent"] = "command_intent"
    command_id: str
    args: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    explanation_fa: str = ""
    needs_clarification: bool = False
    source: Literal["local", "llm"] = "local"


class ExecutionPlan(BaseModel):
    command_id: str
    title_fa: str
    description_fa: str
    argv: list[str]
    risk: RiskLevel
    requires_confirmation: bool
    run_mode: RunMode
    explanation_fa: str
    project_path: str


class RunResult(BaseModel):
    ok: bool
    command_id: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    message_fa: str = ""
    duration_ms: int = 0


class HistoryItem(BaseModel):
    timestamp: str
    user_text: str = ""
    command_id: str
    title_fa: str
    risk: RiskLevel
    project_path: str
    ok: bool
    exit_code: int | None = None
    output_preview: str = ""

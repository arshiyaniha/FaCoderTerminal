from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from pydantic import ValidationError

from .models import LLMSettings, IntentResult


class LLMClientError(Exception):
    pass


class LLMClient:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings

    def is_configured(self) -> bool:
        return bool(self.settings.enabled and self.settings.base_url and self.settings.api_key and self.settings.model)

    def test_connection(self) -> dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "message_fa": "تنظیمات مدل کامل نیست."}
        try:
            result = self.parse_intent("سلام", [])
            return {"ok": True, "message_fa": "اتصال به مدل برقرار شد.", "sample": result.model_dump()}
        except Exception as exc:
            return {"ok": False, "message_fa": f"اتصال به مدل ناموفق بود: {exc}"}

    def parse_intent(self, user_text: str, candidates: list[dict[str, Any]]) -> IntentResult:
        if not self.is_configured():
            raise LLMClientError("تنظیمات مدل کامل نیست.")

        endpoint = self.settings.base_url.rstrip("/") + "/chat/completions"
        system_prompt = (
            "You are an intent parser for a Persian developer command app. "
            "Return only valid JSON. Choose only one command_id from the provided candidates. "
            "Never invent command_id. Never write shell commands. "
            "If unclear, set needs_clarification=true and use command_id='unknown.none'."
        )
        user_prompt = {
            "user_text": user_text,
            "candidate_commands": candidates,
            "required_json_schema": {
                "type": "command_intent",
                "command_id": "string",
                "args": {},
                "confidence": "number 0..1",
                "explanation_fa": "short Persian explanation",
                "needs_clarification": "boolean",
            },
        }
        payload = {
            "model": self.settings.model,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.settings.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise LLMClientError(f"خطای HTTP از provider: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError("ارتباط با provider برقرار نشد.") from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            parsed["source"] = "llm"
            return IntentResult.model_validate(parsed)
        except (KeyError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise LLMClientError("پاسخ مدل ساختار JSON معتبر نداشت.") from exc

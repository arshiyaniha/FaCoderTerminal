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

    def endpoint(self) -> str:
        base = self.settings.base_url.strip().rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def test_connection(self) -> dict[str, Any]:
        if not self.is_configured():
            return {"ok": False, "message_fa": "تنظیمات مدل کامل نیست."}
        try:
            raw = self.chat_completion("سلام! فقط یک کلمه جواب بده.", max_tokens=40)
            preview = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "ok": True,
                "message_fa": "اتصال به مدل برقرار شد.",
                "endpoint": self.endpoint(),
                "response_preview": preview,
            }
        except Exception as exc:
            return {
                "ok": False,
                "message_fa": f"اتصال به مدل ناموفق بود: {exc}",
                "endpoint": self.endpoint() if self.settings.base_url else "",
            }

    def chat_completion(self, prompt: str, max_tokens: int | None = None) -> dict[str, Any]:
        payload = {
            "model": self.settings.model,
            "temperature": self.settings.temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        return self._post(payload)

    def parse_intent(self, user_text: str, candidates: list[dict[str, Any]]) -> IntentResult:
        if not self.is_configured():
            raise LLMClientError("تنظیمات مدل کامل نیست.")

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

        data = self._post(payload)
        try:
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            parsed["source"] = "llm"
            return IntentResult.model_validate(parsed)
        except (KeyError, json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise LLMClientError("پاسخ مدل ساختار JSON معتبر نداشت.") from exc

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            self.endpoint(),
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
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                detail = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                detail = ""
            if detail:
                raise LLMClientError(f"خطای HTTP از provider: {exc.code} - {detail}") from exc
            raise LLMClientError(f"خطای HTTP از provider: {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError("ارتباط با provider برقرار نشد.") from exc
        except json.JSONDecodeError as exc:
            raise LLMClientError("پاسخ provider JSON معتبر نبود.") from exc

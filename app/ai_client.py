from __future__ import annotations

import json
import re
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
            return {"ok": True, "message_fa": "اتصال به مدل برقرار شد.", "endpoint": self.endpoint(), "response_preview": preview}
        except Exception as exc:
            return {"ok": False, "message_fa": f"اتصال به مدل ناموفق بود: {exc}", "endpoint": self.endpoint() if self.settings.base_url else ""}

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
            "You are a strict JSON intent parser for a Persian developer command app. "
            "Return exactly one JSON object and nothing else. "
            "Choose command_id only from candidate_commands. Never invent command_id. "
            "Never write shell commands. If unclear, use command_id='unknown.none' and needs_clarification=true. "
            "No markdown. No explanation outside JSON."
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
            "example_valid_output": {
                "type": "command_intent",
                "command_id": "git.status",
                "args": {},
                "confidence": 0.91,
                "explanation_fa": "درخواست شما به بررسی وضعیت گیت مربوط است.",
                "needs_clarification": False,
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
            content = data["choices"][0]["message"].get("content", "")
            parsed = self._parse_json_object(content)
            parsed["source"] = "llm"
            return IntentResult.model_validate(parsed)
        except (KeyError, ValidationError, TypeError, ValueError) as exc:
            preview = ""
            try:
                preview = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))[:300]
            except Exception:
                preview = ""
            raise LLMClientError(f"پاسخ مدل به JSON قابل اجرا تبدیل نشد. پیش‌نمایش پاسخ: {preview}") from exc

    @staticmethod
    def _parse_json_object(content: str) -> dict[str, Any]:
        text = (content or "").strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            return json.loads(fenced.group(1))

        if text.startswith("{") and text.endswith("}"):
            return json.loads(text)

        start = text.find("{")
        if start == -1:
            raise ValueError("no json object found")

        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start : index + 1])
        raise ValueError("json object not closed")

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            self.endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.settings.api_key}"},
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

from __future__ import annotations

from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover
    fuzz = None

from .models import CatalogCommand, IntentResult
from .normalizer import normalize_for_match


class LocalMatcher:
    def __init__(self, commands: list[CatalogCommand]) -> None:
        self.commands = commands

    def match(self, text: str) -> IntentResult | None:
        needle = normalize_for_match(text)
        if not needle:
            return None

        best_command: CatalogCommand | None = None
        best_score = 0.0

        for command in self.commands:
            phrases = [command.title_fa, command.description_fa, *command.aliases_fa, command.id]
            for phrase in phrases:
                score = self._score(needle, normalize_for_match(phrase))
                if score > best_score:
                    best_score = score
                    best_command = command

        if best_command and best_score >= 0.86:
            return IntentResult(
                command_id=best_command.id,
                confidence=round(best_score, 3),
                explanation_fa="درخواست با دستورهای فارسی موجود در Knowledge Base تطبیق داده شد.",
                source="local",
            )
        return None

    @staticmethod
    def _score(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        if left == right:
            return 1.0
        if left in right or right in left:
            return 0.92
        if fuzz is not None:
            return float(fuzz.token_set_ratio(left, right)) / 100.0
        return SequenceMatcher(None, left, right).ratio()

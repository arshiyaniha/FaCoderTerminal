from __future__ import annotations

from .models import CatalogCommand, RiskLevel


class SecurityDecision:
    def __init__(self, allowed: bool, requires_confirmation: bool, message_fa: str) -> None:
        self.allowed = allowed
        self.requires_confirmation = requires_confirmation
        self.message_fa = message_fa

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "requires_confirmation": self.requires_confirmation,
            "message_fa": self.message_fa,
        }


class SecurityEngine:
    def evaluate(self, command: CatalogCommand) -> SecurityDecision:
        if command.risk == RiskLevel.BLOCKED:
            return SecurityDecision(False, False, "این عملیات توسط سیاست امنیتی برنامه مجاز نیست.")

        if command.risk in {RiskLevel.MEDIUM, RiskLevel.DANGEROUS} or command.requires_confirmation:
            return SecurityDecision(
                True,
                True,
                "این عملیات قبل از اجرا نیازمند تأیید شماست.",
            )

        return SecurityDecision(True, False, "این عملیات در سطح امن طبقه‌بندی شده است.")

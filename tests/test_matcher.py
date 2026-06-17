from pathlib import Path

from app.catalog import CommandCatalog
from app.matcher import LocalMatcher


def test_persian_matcher_detects_git_status() -> None:
    catalog = CommandCatalog(Path(__file__).resolve().parents[1])
    catalog.load()
    matcher = LocalMatcher(catalog.all())
    result = matcher.match("وضعیت گیت پروژه را بررسی کن")
    assert result is not None
    assert result.command_id == "git.status"
    assert result.source == "local"


def test_persian_matcher_returns_none_for_unknown_text() -> None:
    catalog = CommandCatalog(Path(__file__).resolve().parents[1])
    catalog.load()
    matcher = LocalMatcher(catalog.all())
    result = matcher.match("یک متن کاملاً نامرتبط برای تست")
    assert result is None

from pathlib import Path

from app.catalog import CommandCatalog


def test_catalog_loads_commands() -> None:
    catalog = CommandCatalog(Path(__file__).resolve().parents[1])
    catalog.load()
    command_ids = {command.id for command in catalog.all()}
    assert "git.status" in command_ids
    assert "system.python.version" in command_ids


def test_every_command_has_persian_aliases() -> None:
    catalog = CommandCatalog(Path(__file__).resolve().parents[1])
    catalog.load()
    for command in catalog.all():
        assert command.title_fa
        assert command.description_fa
        assert command.aliases_fa
        assert command.argv_template

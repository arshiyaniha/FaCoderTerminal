from __future__ import annotations

from pathlib import Path
from typing import Any

from simple_terminal.simple_pty import SimplePtySession


class SimpleTerminalAPI:
    def __init__(self) -> None:
        self.session = SimplePtySession()

    def start(self, cwd: str = "") -> dict[str, Any]:
        start_dir = cwd or str(Path.cwd())
        return self.session.start(start_dir)

    def write(self, text: str) -> dict[str, Any]:
        return self.session.write(text)

    def read(self) -> dict[str, Any]:
        return self.session.read()

    def resize(self, cols: int, rows: int) -> dict[str, Any]:
        return self.session.resize(cols, rows)

    def stop(self) -> dict[str, Any]:
        return self.session.stop()

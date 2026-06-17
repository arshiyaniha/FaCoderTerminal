from __future__ import annotations

import queue
import re
import threading
from pathlib import Path

_ANSI_PATTERN = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


class EmbeddedSession:
    def __init__(self) -> None:
        self.process = None
        self.output: queue.Queue[str] = queue.Queue()
        self.reader: threading.Thread | None = None
        self.lock = threading.Lock()

    def start(self, cwd: str) -> dict[str, object]:
        try:
            from winpty import PtyProcess
        except Exception as exc:
            return {
                "ok": False,
                "message_fa": "برای ترمینال داخلی باید pywinpty نصب باشد.",
                "technical": str(exc),
            }

        with self.lock:
            if self.process is not None and self.process.isalive():
                return {"ok": True, "message_fa": "session already running"}

            path = Path(cwd).expanduser() if cwd else Path.cwd()
            if not path.exists() or not path.is_dir():
                path = Path.cwd()

            startup = (
                "Remove-Module PSReadLine -ErrorAction SilentlyContinue; "
                "$PSStyle.OutputRendering='PlainText'; "
                "function prompt { 'PS ' + (Get-Location) + '> ' }"
            )
            self.process = PtyProcess.spawn(
                f"powershell.exe -NoLogo -NoProfile -NoExit -Command \"{startup}\"",
                cwd=str(path),
            )
            self.reader = threading.Thread(target=self._read_loop, daemon=True)
            self.reader.start()
            return {"ok": True, "message_fa": "ترمینال داخلی آماده است.", "cwd": str(path)}

    def write(self, text: str) -> dict[str, object]:
        with self.lock:
            if self.process is None or not self.process.isalive():
                return {"ok": False, "message_fa": "ترمینال داخلی فعال نیست."}
            self.process.write(text)
            return {"ok": True}

    def read(self) -> dict[str, object]:
        chunks: list[str] = []
        while True:
            try:
                chunks.append(self.output.get_nowait())
            except queue.Empty:
                break
        return {"ok": True, "output": "".join(chunks)}

    def stop(self) -> dict[str, object]:
        with self.lock:
            if self.process is not None and self.process.isalive():
                self.process.terminate()
            self.process = None
        return {"ok": True}

    def _read_loop(self) -> None:
        while True:
            try:
                if self.process is None or not self.process.isalive():
                    break
                data = self.process.read(4096)
                if data:
                    self.output.put(self._clean_output(data))
            except Exception as exc:
                self.output.put(f"\n[terminal read error] {exc}\n")
                break

    @staticmethod
    def _clean_output(data: str) -> str:
        value = _ANSI_PATTERN.sub("", data)
        value = value.replace("\x07", "")
        return value

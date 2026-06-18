from __future__ import annotations

import base64
import os
import queue
import threading
from pathlib import Path
from typing import Any


class SimplePtySession:
    def __init__(self) -> None:
        self.process = None
        self.output: queue.Queue[str] = queue.Queue()
        self.reader: threading.Thread | None = None
        self.lock = threading.Lock()

    def start(self, cwd: str) -> dict[str, Any]:
        try:
            from winpty import PtyProcess
        except Exception as exc:
            return {
                "ok": False,
                "message": "pywinpty is not installed. Run: pip install -r requirements.txt",
                "technical": str(exc),
            }

        with self.lock:
            if self.process is not None and self.process.isalive():
                return {"ok": True, "message": "Shell is already running."}

            path = Path(cwd).expanduser()
            if not path.exists() or not path.is_dir():
                path = Path.cwd()

            attempted: list[dict[str, str]] = []
            for command in self._candidate_shell_commands():
                try:
                    self.process = PtyProcess.spawn(command, cwd=str(path))
                    attempted.append({"command": command, "result": "started"})
                    break
                except Exception as exc:
                    attempted.append({"command": command, "result": str(exc)})
                    self.process = None

            if self.process is None:
                return {
                    "ok": False,
                    "message": "No shell could be started.",
                    "attempted": attempted,
                }

            self.reader = threading.Thread(target=self._read_loop, daemon=True)
            self.reader.start()
            return {"ok": True, "cwd": str(path), "shell": attempted[-1]["command"], "attempted": attempted}

    def write(self, text: str) -> dict[str, Any]:
        with self.lock:
            if self.process is None or not self.process.isalive():
                return {"ok": False, "message": "Shell is not running."}
            self.process.write(text)
            return {"ok": True}

    def read(self) -> dict[str, Any]:
        chunks: list[str] = []
        while True:
            try:
                chunks.append(self.output.get_nowait())
            except queue.Empty:
                break
        return {"ok": True, "output": "".join(chunks)}

    def resize(self, cols: int, rows: int) -> dict[str, Any]:
        with self.lock:
            if self.process is None or not self.process.isalive():
                return {"ok": False, "message": "Shell is not running."}
            try:
                self.process.setwinsize(rows, cols)
                return {"ok": True}
            except Exception as exc:
                return {"ok": False, "message": str(exc)}

    def stop(self) -> dict[str, Any]:
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
                    self.output.put(data)
            except Exception as exc:
                self.output.put(f"\r\n[read error] {exc}\r\n")
                break

    @staticmethod
    def _powershell_startup_script() -> str:
        # PowerShell's -EncodedCommand expects UTF-16LE.
        # This startup script keeps input/output on UTF-8 so Persian text renders correctly.
        # It also replaces cd/chdir/sl with a tolerant version that accepts unquoted paths
        # copied from Explorer, including Persian paths and paths containing spaces.
        return r"""
try { chcp.com 65001 | Out-Null } catch {}
try { [Console]::InputEncoding = [System.Text.UTF8Encoding]::new() } catch {}
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch {}
try { $OutputEncoding = [Console]::OutputEncoding } catch {}
try { $PSStyle.OutputRendering = 'Ansi' } catch {}

foreach ($name in @('cd', 'chdir', 'sl')) {
    try { Remove-Item "Alias:$name" -Force -ErrorAction SilentlyContinue } catch {}
}

function global:cd {
    [CmdletBinding()]
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]] $PathParts
    )

    if (-not $PathParts -or $PathParts.Count -eq 0) {
        Microsoft.PowerShell.Management\Set-Location -Path $HOME
        return
    }

    $target = ($PathParts -join ' ').Trim()
    $target = $target.Trim('"').Trim("'")

    if ($target -match '^file:///') {
        try { $target = ([System.Uri] $target).LocalPath } catch {}
    }

    $target = [Environment]::ExpandEnvironmentVariables($target)
    Microsoft.PowerShell.Management\Set-Location -LiteralPath $target
}

function global:chdir {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments = $true)][string[]] $PathParts)
    cd @PathParts
}

function global:sl {
    [CmdletBinding()]
    param([Parameter(ValueFromRemainingArguments = $true)][string[]] $PathParts)
    cd @PathParts
}
""".strip()

    @classmethod
    def _candidate_shell_commands(cls) -> list[str]:
        startup = cls._powershell_startup_script()
        encoded = base64.b64encode(startup.encode("utf-16le")).decode("ascii")
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        powershell = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        cmd = system_root / "System32" / "cmd.exe"

        commands: list[str] = []
        if os.environ.get("SIMPLE_TERMINAL_USE_PWSH") == "1":
            commands.append(f'pwsh.exe -NoLogo -NoProfile -NoExit -EncodedCommand {encoded}')

        if powershell.exists():
            commands.append(f'"{powershell}" -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -EncodedCommand {encoded}')

        commands.append(f'powershell.exe -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass -EncodedCommand {encoded}')

        # Last-resort fallback. This is not PowerShell, but keeps the app usable and confirms PTY works.
        if cmd.exists():
            commands.append(f'"{cmd}" /K chcp 65001')
        commands.append("cmd.exe /K chcp 65001")
        return commands

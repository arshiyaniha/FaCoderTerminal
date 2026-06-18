from __future__ import annotations

import os
import platform
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class SimplePtySession:
    def __init__(self) -> None:
        self.process = None
        self.output: queue.Queue[str] = queue.Queue()
        self.reader: threading.Thread | None = None
        self.lock = threading.Lock()
        self.active_command = ""
        self.shell_kind = ""

    def start(self, cwd: str) -> dict[str, Any]:
        diagnostics = self._collect_diagnostics(cwd)
        try:
            from winpty import PtyProcess
            diagnostics.append("[OK] winpty import succeeded")
        except Exception as exc:
            diagnostics.append(f"[FAIL] winpty import failed: {exc!r}")
            return {
                "ok": False,
                "message": "pywinpty is not installed. Run: pip install -r requirements.txt",
                "technical": str(exc),
                "diagnostic": self._format_diagnostics(diagnostics),
            }

        with self.lock:
            if self.process is not None and self.process.isalive():
                diagnostics.append("[OK] Existing shell is already alive")
                return {"ok": True, "message": "Shell is already running.", "diagnostic": self._format_diagnostics(diagnostics)}

            path = Path(cwd).expanduser()
            if not path.exists() or not path.is_dir():
                diagnostics.append(f"[WARN] Requested cwd is invalid, fallback to current cwd: {path}")
                path = Path.cwd()
            diagnostics.append(f"[INFO] Final cwd: {path}")

            attempted: list[dict[str, str]] = []
            candidates = self._candidate_shell_commands()
            diagnostics.append("[INFO] Candidate shells:")
            for index, candidate in enumerate(candidates, start=1):
                diagnostics.append(f"  {index}. {candidate['kind']}: {candidate['command']}")

            for candidate in candidates:
                command = candidate["command"]
                diagnostics.append(f"[TRY] PTY spawn: {command}")
                try:
                    self.process = PtyProcess.spawn(command, cwd=str(path))
                    self.active_command = command
                    self.shell_kind = candidate["kind"]
                    time.sleep(0.35)
                    alive = self._safe_isalive()
                    attempted.append({"command": command, "result": f"spawn returned; isalive={alive}"})
                    diagnostics.append(f"[INFO] PTY spawn returned. isalive_after_350ms={alive}")
                    if alive == "True":
                        break
                    diagnostics.append("[WARN] Shell died immediately after spawn; trying next candidate.")
                    self.process = None
                except Exception as exc:
                    attempted.append({"command": command, "result": repr(exc)})
                    diagnostics.append(f"[FAIL] PTY spawn exception: {exc!r}")
                    self.process = None

            if self.process is None:
                diagnostics.append("[FAIL] No shell could be started through PTY")
                return {
                    "ok": False,
                    "message": "No shell could be started.",
                    "attempted": attempted,
                    "diagnostic": self._format_diagnostics(diagnostics),
                }

            diagnostics.append(f"[OK] Selected shell kind: {self.shell_kind}")
            diagnostics.append(f"[OK] Selected shell command: {self.active_command}")
            self.output.put(self._format_diagnostics(diagnostics) + "\r\n")

            self.reader = threading.Thread(target=self._read_loop, daemon=True)
            self.reader.start()
            self._inject_startup_script()
            return {
                "ok": True,
                "cwd": str(path),
                "shell": self.active_command,
                "attempted": attempted,
                "diagnostic": self._format_diagnostics(diagnostics),
            }

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
                if self.process is None:
                    self.output.put("\r\n[DIAG] process object is None; read loop stopped\r\n")
                    break
                if not self.process.isalive():
                    self.output.put(
                        "\r\n[DIAG] PTY process is no longer alive before read.\r\n"
                        f"[DIAG] active shell: {self.active_command}\r\n"
                    )
                    break
                data = self.process.read(4096)
                if data:
                    self.output.put(data)
            except Exception as exc:
                alive = self._safe_isalive()
                self.output.put(
                    "\r\n[read error] " + str(exc) + "\r\n"
                    "[DIAG] Read loop exception details:\r\n"
                    f"  exception_type: {type(exc).__name__}\r\n"
                    f"  exception_repr: {exc!r}\r\n"
                    f"  process_isalive: {alive}\r\n"
                    f"  active_shell: {self.active_command}\r\n"
                    "[DIAG] If this happens after a shell prompt appeared, the child shell exited or crashed.\r\n"
                )
                break

    def _inject_startup_script(self) -> None:
        if self.process is None or not self.process.isalive():
            self.output.put("\r\n[DIAG] Startup script not injected because shell is not alive.\r\n")
            return
        try:
            if self.shell_kind == "powershell":
                self.output.put("\r\n[INFO] Injecting PowerShell UTF-8 and smart cd startup script...\r\n")
                self.process.write(self._powershell_startup_script() + "\r")
            elif self.shell_kind == "cmd":
                self.output.put("\r\n[INFO] CMD fallback is active. PowerShell-specific smart cd is not available.\r\n")
        except Exception as exc:
            self.output.put(f"\r\n[DIAG] Startup script injection failed: {exc!r}\r\n")

    def _safe_isalive(self) -> str:
        try:
            if self.process is None:
                return "no-process"
            return str(self.process.isalive())
        except Exception as exc:
            return f"isalive-error: {exc!r}"

    @staticmethod
    def _short_env(value: str, limit: int = 420) -> str:
        value = value or ""
        if len(value) <= limit:
            return value
        return value[:limit] + " ...[truncated]"

    @classmethod
    def _collect_diagnostics(cls, cwd: str) -> list[str]:
        lines: list[str] = []
        lines.append("========== Simple Persian PowerShell Diagnostics ==========")
        lines.append(f"[INFO] timestamp: {datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"[INFO] frozen: {getattr(sys, 'frozen', False)}")
        lines.append(f"[INFO] sys.executable: {sys.executable}")
        lines.append(f"[INFO] sys.argv: {sys.argv}")
        lines.append(f"[INFO] python: {sys.version.replace(os.linesep, ' ')}")
        lines.append(f"[INFO] platform: {platform.platform()}")
        lines.append(f"[INFO] machine: {platform.machine()}")
        lines.append(f"[INFO] cwd argument: {cwd}")
        lines.append(f"[INFO] process cwd: {Path.cwd()}")
        lines.append(f"[INFO] SystemRoot: {os.environ.get('SystemRoot', '')}")
        lines.append(f"[INFO] ComSpec: {os.environ.get('ComSpec', '')}")
        lines.append(f"[INFO] PATH: {cls._short_env(os.environ.get('PATH', ''))}")

        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        powershell = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        syswow_powershell = system_root / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        cmd = system_root / "System32" / "cmd.exe"
        pwsh = "pwsh.exe"

        for label, path in [
            ("powershell_system32", powershell),
            ("powershell_syswow64", syswow_powershell),
            ("cmd_system32", cmd),
        ]:
            lines.append(f"[CHECK] {label}: {path} exists={path.exists()}")

        lines.extend(cls._subprocess_probe("powershell full path", str(powershell), ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], powershell.exists()))
        lines.extend(cls._subprocess_probe("powershell PATH", "powershell.exe", ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], True))
        lines.extend(cls._subprocess_probe("cmd full path", str(cmd), ["/C", "echo CMD_OK"], cmd.exists()))
        if os.environ.get("SIMPLE_TERMINAL_USE_PWSH") == "1":
            lines.extend(cls._subprocess_probe("pwsh PATH", pwsh, ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"], True))

        return lines

    @staticmethod
    def _subprocess_probe(label: str, exe: str, args: list[str], should_run: bool) -> list[str]:
        lines: list[str] = []
        if not should_run:
            lines.append(f"[SKIP] subprocess probe {label}: executable not found")
            return lines
        try:
            completed = subprocess.run(
                [exe, *args],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="replace",
            )
            stdout = (completed.stdout or "").strip().replace("\r\n", " | ").replace("\n", " | ")
            stderr = (completed.stderr or "").strip().replace("\r\n", " | ").replace("\n", " | ")
            lines.append(f"[PROBE] {label}: returncode={completed.returncode}")
            lines.append(f"        stdout={stdout[:300]}")
            lines.append(f"        stderr={stderr[:300]}")
        except Exception as exc:
            lines.append(f"[PROBE-FAIL] {label}: {type(exc).__name__}: {exc}")
        return lines

    @staticmethod
    def _format_diagnostics(lines: list[str]) -> str:
        return "\r\n".join(lines) + "\r\n==========================================================="

    @staticmethod
    def _powershell_startup_script() -> str:
        return r"""
chcp.com 65001 | Out-Null
try { [Console]::InputEncoding = [System.Text.UTF8Encoding]::new() } catch {}
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch {}
try { $OutputEncoding = [Console]::OutputEncoding } catch {}
foreach ($name in @('cd','chdir','sl')) { try { Remove-Item "Alias:$name" -Force -ErrorAction SilentlyContinue } catch {} }
function global:cd { param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PathParts) if(-not $PathParts){ Microsoft.PowerShell.Management\Set-Location -Path $HOME; return }; $target=($PathParts -join ' ').Trim().Trim('"').Trim("'"); if($target -match '^file:///'){ try{ $target=([System.Uri]$target).LocalPath }catch{} }; $target=[Environment]::ExpandEnvironmentVariables($target); Microsoft.PowerShell.Management\Set-Location -LiteralPath $target }
function global:chdir { param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PathParts) cd @PathParts }
function global:sl { param([Parameter(ValueFromRemainingArguments=$true)][string[]]$PathParts) cd @PathParts }
Write-Host '[OK] UTF-8 and smart cd are active.'
""".strip()

    @classmethod
    def _candidate_shell_commands(cls) -> list[dict[str, str]]:
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        powershell = system_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        cmd = system_root / "System32" / "cmd.exe"

        candidates: list[dict[str, str]] = []
        if os.environ.get("SIMPLE_TERMINAL_USE_PWSH") == "1":
            candidates.append({"kind": "powershell", "command": "pwsh.exe -NoLogo -NoProfile -NoExit"})

        if powershell.exists():
            candidates.append({"kind": "powershell", "command": f"{powershell} -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass"})

        candidates.append({"kind": "powershell", "command": "powershell.exe -NoLogo -NoProfile -NoExit -ExecutionPolicy Bypass"})

        if cmd.exists():
            candidates.append({"kind": "cmd", "command": f"{cmd} /K chcp 65001"})
        candidates.append({"kind": "cmd", "command": "cmd.exe /K chcp 65001"})
        return candidates

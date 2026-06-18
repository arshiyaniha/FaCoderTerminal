from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .models import AppSettings, ServerSettings


class ProjectSyncService:
    def __init__(self, settings: AppSettings, app_root: Path) -> None:
        self.settings = settings
        self.app_root = app_root

    def health(self) -> dict[str, Any]:
        local = self.local_state()
        github = self.github_state()
        server = self.server_state()
        return {
            "ok": True,
            "local": local,
            "github": github,
            "server": server,
            "summary": self._summary(local, github, server),
        }

    def local_state(self) -> dict[str, Any]:
        path = Path(self.settings.default_project_path or self.app_root).expanduser()
        if not path.exists() or not path.is_dir():
            return {"ok": False, "message_fa": "مسیر پروژه لوکال معتبر نیست.", "path": str(path)}
        branch = self._run(["git", "branch", "--show-current"], cwd=path)
        head = self._run(["git", "rev-parse", "HEAD"], cwd=path)
        remote = self._run(["git", "remote", "get-url", "origin"], cwd=path)
        dirty = self._run(["git", "status", "--short"], cwd=path)
        return {
            "ok": branch["ok"] and head["ok"],
            "path": str(path),
            "branch": branch["stdout"].strip(),
            "head": head["stdout"].strip(),
            "remote": remote["stdout"].strip(),
            "dirty": bool(dirty["stdout"].strip()),
            "status_short": dirty["stdout"].strip(),
            "message_fa": "پروژه لوکال خوانده شد." if branch["ok"] else "Git روی مسیر لوکال آماده نیست.",
        }

    def github_state(self) -> dict[str, Any]:
        path = Path(self.settings.default_project_path or self.app_root).expanduser()
        branch = self.settings.github.default_branch or "main"
        fetch = self._run(["git", "fetch", "origin", branch], cwd=path)
        remote_head = self._run(["git", "rev-parse", f"origin/{branch}"], cwd=path)
        return {
            "ok": remote_head["ok"],
            "branch": branch,
            "head": remote_head["stdout"].strip(),
            "message_fa": "وضعیت GitHub خوانده شد." if remote_head["ok"] else fetch.get("stderr") or "GitHub قابل بررسی نیست.",
        }

    def server_state(self) -> dict[str, Any]:
        server = self.settings.server
        if not server.host or not server.username or not server.project_path:
            return {"ok": False, "message_fa": "تنظیمات سرور کامل نیست."}
        remote_command = "cd " + self._sh_quote(server.project_path) + " && git branch --show-current && git rev-parse HEAD && git status --short"
        result = self.server_exec(remote_command)
        lines = [line.strip() for line in result.get("stdout", "").splitlines() if line.strip()]
        return {
            "ok": result["ok"] and len(lines) >= 2,
            "host": server.host,
            "project_path": server.project_path,
            "branch": lines[0] if len(lines) >= 1 else "",
            "head": lines[1] if len(lines) >= 2 else "",
            "dirty": len(lines) > 2,
            "status_short": "\n".join(lines[2:]),
            "message_fa": "وضعیت سرور خوانده شد." if result["ok"] else result.get("stderr") or result.get("message_fa"),
        }

    def server_exec(self, remote_command: str) -> dict[str, Any]:
        server = self.settings.server
        if not server.host or not server.username:
            return {"ok": False, "message_fa": "هاست یا نام کاربری سرور تنظیم نشده است."}
        cmd = self._server_base_command(server) + [remote_command]
        return self._run(cmd, cwd=self.app_root, timeout=45)

    def generate_keypair(self) -> dict[str, Any]:
        server = self.settings.server
        key_dir = Path.home() / ".facoderterminal" / "keys"
        key_dir.mkdir(parents=True, exist_ok=True)
        key_file = key_dir / f"{server.name or 'server'}_ed25519"
        if key_file.exists():
            return {"ok": True, "message_fa": "کلید از قبل وجود دارد.", "key_path": str(key_file), "public_key_path": str(key_file) + ".pub"}
        result = self._run(["ssh-keygen", "-t", "ed25519", "-f", str(key_file), "-N", "", "-C", "facoderterminal"], cwd=self.app_root)
        return {
            "ok": result["ok"],
            "message_fa": "کلید بدون رمز ساخته شد." if result["ok"] else "ساخت کلید ناموفق بود.",
            "key_path": str(key_file),
            "public_key_path": str(key_file) + ".pub",
            "stderr": result.get("stderr", ""),
        }

    def _server_base_command(self, server: ServerSettings) -> list[str]:
        cmd = ["ssh", "-p", str(server.port), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
        if server.key_path:
            cmd.extend(["-i", server.key_path])
        cmd.append(f"{server.username}@{server.host}")
        return cmd

    def _run(self, cmd: list[str], cwd: Path, timeout: int = 30) -> dict[str, Any]:
        try:
            completed = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, shell=False)
            return {"ok": completed.returncode == 0, "stdout": completed.stdout, "stderr": completed.stderr, "exit_code": completed.returncode}
        except FileNotFoundError:
            return {"ok": False, "stdout": "", "stderr": "ابزار لازم روی سیستم پیدا نشد.", "exit_code": None}
        except subprocess.TimeoutExpired:
            return {"ok": False, "stdout": "", "stderr": "اجرای دستور بیش از حد طول کشید.", "exit_code": None}
        except OSError as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc), "exit_code": None}

    @staticmethod
    def _sh_quote(value: str) -> str:
        return "'" + value.replace("'", "'\\''") + "'"

    @staticmethod
    def _summary(local: dict[str, Any], github: dict[str, Any], server: dict[str, Any]) -> dict[str, Any]:
        local_head = local.get("head")
        github_head = github.get("head")
        server_head = server.get("head")
        all_known = bool(local_head and github_head and server_head)
        return {
            "all_known": all_known,
            "local_matches_github": bool(local_head and github_head and local_head == github_head),
            "server_matches_github": bool(server_head and github_head and server_head == github_head),
            "local_dirty": bool(local.get("dirty")),
            "server_dirty": bool(server.get("dirty")),
        }

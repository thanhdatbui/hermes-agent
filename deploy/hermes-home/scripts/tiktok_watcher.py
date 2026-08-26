"""Hermes cron wrapper for the TikTok failure watcher (HCM timezone, default-off).

See tiktok_picker.py for the full contract. This wrapper differs only in the
business entrypoint (hermes_cron_watcher.py) and the forward env keys it needs
(it additionally requires HERMES_CRON_REPORT_JSONL). It spawns the target
Python with the child cwd set to the repo root and a strictly allowlisted
environment.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Mapping, Sequence
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

TARGET_PYTHON_DEFAULT = "/d/Taadaa/python-envs/automation/Scripts/python.exe"
TARGET_PYTHON_ENV = "HERMES_CRON_TARGET_PYTHON"
NOW_ENV = "HERMES_CRON_NOW"

ACTIVATION_ENV = "HERMES_CRON_WATCHER_ENABLED"
PERMIT_ENV = "HERMES_CRON_PERMIT_FILE"

BUSINESS_SCRIPT = "python_runner/scripts/hermes_cron_watcher.py"

ALLOWED_FORWARD_ENV = frozenset(
    {
        "TAADAA_HOST_CONFIG",
        "HERMES_CRON_STATE_ROOT",
        "HERMES_CRON_SOURCE_CONFIG",
        "HERMES_CRON_OFFLINE_ROOT",
        "HERMES_CRON_REPORT_JSONL",
    }
)

REQUIRED_FORWARD_ENV = frozenset(
    {
        "HERMES_CRON_STATE_ROOT",
        "HERMES_CRON_SOURCE_CONFIG",
        "HERMES_CRON_OFFLINE_ROOT",
        "HERMES_CRON_REPORT_JSONL",
    }
)

_ARG_MAP = {
    "HERMES_CRON_STATE_ROOT": "--state-root",
    "HERMES_CRON_SOURCE_CONFIG": "--source-config",
    "HERMES_CRON_OFFLINE_ROOT": "--offline-root",
    "HERMES_CRON_REPORT_JSONL": "--report-jsonl",
}


def repo_root() -> Path:
    """Resolve the repository root (pinned env wins, then walk up to .git).

    Deployed wrapper runs from ~/hermes/scripts/ (no .git ancestor); the
    operator-pinned HERMES_CRON_REPO (env.json) resolves the real repo.
    """
    pinned = os.environ.get("HERMES_CRON_REPO")
    if pinned:
        candidate = Path(pinned)
        if (candidate / ".git").is_dir() or (candidate / ".git").is_file():
            return candidate
    # Hermes cron runs no_agent scripts with cwd = HERMES_HOME/scripts, NOT
    # the job workdir (scheduler._run_job_script uses cwd=path.parent).  Probe
    # known candidate roots for the operator-pinned repo.
    for root in ("D:/Taadaa/tiktok-luot nuoi acc", "D:/Taadaa/tiktok-follow",
                 "D:/Taadaa/automation-core"):
        candidate = Path(root)
        if (candidate / ".git").is_dir() or (candidate / ".git").is_file():
            return candidate
    # Hermes cron runs the wrapper with cwd possibly = repo (manual run).
    try:
        cwd = Path(os.getcwd()).resolve()
        if (cwd / ".git").is_dir() or (cwd / ".git").is_file():
            return cwd
    except OSError:
        pass
    here = Path(__file__).resolve()
    for ancestor in (here, *here.parents):
        marker = ancestor / ".git"
        if marker.is_dir() or marker.is_file():
            return ancestor
    # Fall back to the package parent (scripts -> repo).
    return here.parents[1]


def target_python() -> str:
    """Resolve the target Python as a Windows path (CreateProcess-safe).

    The default is expressed as an MSYS path (``/d/...``) which the Windows
    ``CreateProcess`` used by ``subprocess`` cannot resolve directly; convert
    it to ``D:\\...`` when the env override is absent.
    """
    value = os.environ.get(TARGET_PYTHON_ENV) or TARGET_PYTHON_DEFAULT
    if value.startswith("/") and len(value) > 2 and value[2] == "/":
        drive = f"{value[1].upper()}:"
        rest = value[3:].replace("/", "\\")
        return drive + "\\" + rest
    return value


def now_hcmc() -> datetime:
    override = os.environ.get(NOW_ENV)
    if override:
        dt = datetime.fromisoformat(override)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=HCMC)
        return dt
    return datetime.now(HCMC)


def compute_logical_day(now: datetime) -> str | None:
    if 2 <= now.hour <= 5:
        return None
    day = now.date()
    if now.hour < 2:
        day = day - timedelta(days=1)
    return day.isoformat()


def _config_digest(env: Mapping[str, str]) -> str:
    path = env.get("HERMES_CRON_SOURCE_CONFIG")
    if path and Path(path).is_file():
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return "no-config"


def deterministic_seed(day: str, config_digest: str) -> int:
    material = f"{day}|{config_digest}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def is_activated(env: Mapping[str, str]) -> bool:
    if env.get(ACTIVATION_ENV) == "1":
        return True
    permit = env.get(PERMIT_ENV) or _default_permit_file()
    if permit:
        p = Path(permit)
        try:
            return p.is_file() and not p.is_symlink()
        except OSError:
            return False
    return False


def _default_permit_file() -> Path:
    """Repo-anchored activation permit (cron tool cannot set env).

    The Hermes cron job runs the wrapper with the repository as its working
    directory and no custom environment, so activation is derived from a
    regular, non-symlink permit file under ``runtime/hermes-cron/permits/``
    named ``<wrapper-kind>.permit``. Absence of the file keeps the wrapper
    inert (fail-closed), matching the previous env-only contract.
    """
    return repo_root() / "runtime" / "hermes-cron" / "permits" / f"{Path(__file__).stem}.permit"


def build_child_env(env: Mapping[str, str]) -> dict[str, str]:
    child: dict[str, str] = {}
    child["TZ"] = "Asia/Ho_Chi_Minh"
    child["PATH"] = env.get("HERMES_CRON_CHILD_PATH", "")
    child["PYTHONPATH"] = str(repo_root())
    child["PYTHONTZPATH"] = env.get("HERMES_CRON_TZDATA", "D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo")
    for key in ALLOWED_FORWARD_ENV:
        value = env.get(key)
        if value is not None:
            child[key] = value
    # Non-secret Windows infrastructure required for the child process to
    # start (e.g. python.exe needs SystemRoot); forwarded only when present.
    for key in ("SystemRoot", "SystemDrive", "ComSpec", "PATHEXT", "TEMP", "TMP"):
        value = env.get(key)
        if value is not None:
            child[key] = value
    return child


def repo_env_overrides() -> dict[str, str]:
    """Repo-anchored env fallback for a cron run.

    The Hermes cron tool cannot set per-job environment variables, so the
    live config (state root, source config, offline root, report JSONL)
    lives in a regular JSON file at ``<repo>/runtime/hermes-cron/env.json``.
    The wrapper merges those values UNDER the process environment (process
    env wins). Absence of the file — or of a required key after the merge —
    keeps the wrapper fail-closed (exit 3, no child), exactly like the
    env-only contract. The file is created by the operator when live
    execution is approved.
    """
    path = repo_root() / "runtime" / "hermes-cron" / "env.json"
    try:
        if not path.is_file() or path.is_symlink():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if isinstance(k, str) and isinstance(v, (str, int))}


def merged_env(env: Mapping[str, str]) -> dict[str, str]:
    """Process env merged with repo env overrides (process env wins)."""
    merged = dict(env)
    for key, value in repo_env_overrides().items():
        merged.setdefault(key, value)
    return merged


def build_business_argv(
    env: Mapping[str, str],
    day: str,
    seed: int,
    as_of: str,
    reference_time: str,
) -> list[str]:
    argv: list[str] = [target_python(), BUSINESS_SCRIPT]
    for env_key, flag in _ARG_MAP.items():
        value = env.get(env_key)
        if value is None:
            continue
        argv.append(flag)
        argv.append(value)
    argv.append("--day")
    argv.append(day)

    argv.append("--as-of")
    argv.append(as_of)
    argv.append("--reference-time")
    argv.append(reference_time)
    return argv


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if args:
        sys.stderr.write("tiktok_watcher: business argv rejected (use activation env)\n")
        return 2

    env = merged_env(os.environ)
    if not is_activated(env):
        return 0

    now = now_hcmc()
    day = compute_logical_day(now)
    if day is None:
        return 0

    as_of = now.isoformat()
    reference_time = now.isoformat()
    seed = deterministic_seed(day, _config_digest(env))

    missing = [k for k in REQUIRED_FORWARD_ENV if not env.get(k)]
    if missing:
        sys.stderr.write(
            "tiktok_watcher: missing required config: " + ", ".join(sorted(missing)) + "\n"
        )
        return 3

    child_argv = build_business_argv(env, day, seed, as_of, reference_time)
    child_env = build_child_env(env)
    subprocess.run(child_argv, cwd=str(repo_root()), env=child_env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

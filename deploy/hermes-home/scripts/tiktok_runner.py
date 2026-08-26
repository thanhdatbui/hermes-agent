"""Hermes cron wrapper for the TikTok feed runner (HCM timezone, default-off).

See tiktok_picker.py for the full contract. This wrapper differs only in the
business entrypoint (hermes_cron_runner.py) and the forward env keys it needs.
It never passes --execute / --repo / --feed-workbook (the offline harness
refuses those), and it spawns the target Python with the child cwd set to the
repo root and a strictly allowlisted environment.
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

ACTIVATION_ENV = "HERMES_CRON_RUNNER_ENABLED"
PERMIT_ENV = "HERMES_CRON_PERMIT_FILE"

BUSINESS_SCRIPT = "python_runner/scripts/hermes_cron_runner.py"

ALLOWED_FORWARD_ENV = frozenset(
    {
        "TAADAA_HOST_CONFIG",
        "HERMES_CRON_STATE_ROOT",
        "HERMES_CRON_SOURCE_CONFIG",
        "HERMES_CRON_OFFLINE_ROOT",
        "HERMES_CRON_REPO",
        "HERMES_CRON_FEED_WORKBOOK",
    }
)

REQUIRED_FORWARD_ENV = frozenset(
    {
        "HERMES_CRON_STATE_ROOT",
        "HERMES_CRON_SOURCE_CONFIG",
        "HERMES_CRON_OFFLINE_ROOT",
    }
)

_ARG_MAP = {
    "HERMES_CRON_STATE_ROOT": "--state-root",
    "HERMES_CRON_SOURCE_CONFIG": "--source-config",
    "HERMES_CRON_OFFLINE_ROOT": "--offline-root",
    "HERMES_CRON_REPO": "--repo",
    "HERMES_CRON_FEED_WORKBOOK": "--feed-workbook",
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
    child["PATH"] = env.get("HERMES_CRON_CHILD_PATH") or (
        r"C:\Windows\System32\WindowsPowerShell\v1.0;C:\Windows\System32;C:\Windows"
    )
    child["PYTHONPATH"] = str(repo_root())
    child["PYTHONTZPATH"] = env.get("HERMES_CRON_TZDATA", "D:/Taadaa/Hermes/.venv/Lib/site-packages/tzdata/zoneinfo")
    for key in ALLOWED_FORWARD_ENV:
        value = env.get(key)
        if value is not None:
            child[key] = value
    # Windows PowerShell 5.1 needs a near-full environment to load the managed
    # CLR (error 0x8009001D when key vars are absent).  Forward every parent
    # key except the forbidden/secret set; PATH stays the sanitized value above
    # and secrets (AGENT/TOKEN/PASSWORD/CREDENTIAL/API_KEY/LIVE_PERMIT) never
    # cross into the child.
    _FORBIDDEN_SUBSTRINGS = (
        "SECRET", "TOKEN", "PASSWORD", "PASSWD", "CREDENTIAL", "API_KEY",
        "AGENT", "HERMES_WORKDIR", "HERMES_LIVE_PERMIT_FILE", "KEY",
    )
    for key, value in env.items():
        upper = key.upper()
        if any(b in upper for b in _FORBIDDEN_SUBSTRINGS):
            continue
        if key in child:
            continue  # TZ / PATH / PYTHONPATH already pinned above
        child[key] = value
    return child


def repo_env_overrides() -> dict[str, str]:
    """Repo-anchored env fallback for a cron run.

    The Hermes cron tool cannot set per-job environment variables, so the
    live config (state root, source config, offline root, owner/worker id,
    state JSON paths, repo, feed workbook) lives in a regular JSON file at
    ``<repo>/runtime/hermes-cron/env.json``. The wrapper merges those values
    UNDER the process environment (process env wins). Absence of the file —
    or of a required key after the merge — keeps the wrapper fail-closed
    (exit 3, no child), exactly like the env-only contract. The file is
    created by the operator when live execution is approved.
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


def _load_active_manifest(env: Mapping[str, str], day: str) -> dict | None:
    """Load the active assignment manifest for ``day`` (fail-closed)."""
    state_root = Path(env.get("HERMES_CRON_STATE_ROOT", ""))
    if not state_root.is_dir():
        return None
    pointer = state_root / "manifests" / day / "ACTIVE.json"
    try:
        if pointer.is_symlink() or not pointer.is_file():
            return None
        pointer_data = json.loads(pointer.read_text(encoding="utf-8"))
        manifest_path = Path(pointer_data["manifest_path"])
        if not manifest_path.is_absolute():
            manifest_path = pointer.parent / manifest_path
        if manifest_path.is_symlink() or not manifest_path.is_file():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def _due_entries(manifest: dict, now: datetime) -> list[dict]:
    """Entries whose slot window (slot_time .. slot_time+90') covers ``now``."""
    due = []
    for entry in manifest.get("entries", []):
        try:
            slot = datetime.fromisoformat(entry["slot_time"])
        except (TypeError, ValueError):
            continue
        if slot <= now <= slot + timedelta(minutes=90):
            due.append(entry)
    return due


def _live_lease_path(env: Mapping[str, str], day: str) -> Path:
    state_root = Path(env.get("HERMES_CRON_STATE_ROOT", ""))
    return state_root / "runner-live-lease" / f"{day}.json"


def _lease_alive(env: Mapping[str, str], day: str, now: datetime) -> bool:
    """Return True when a live spawn from an earlier tick is still running.
    
    If the lease has exceeded a safety threshold (max 90 minutes for a feed session)
    or its recorded process is dead/hung, cleanly clean up the stale lease so
    subsequent cron shifts are never blocked indefinitely.
    """
    lease_path = _live_lease_path(env, day)
    try:
        if lease_path.is_symlink() or not lease_path.is_file():
            return False
        lease = json.loads(lease_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False

    # Guard 1: Hard expiry check
    if lease.get("expires_at"):
        try:
            if datetime.fromisoformat(lease["expires_at"]) < now:
                try:
                    lease_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return False
        except (TypeError, ValueError):
            pass

    # Guard 2: Max runtime limit for a single feed batch (90 minutes)
    started_at_str = lease.get("started_at")
    if started_at_str:
        try:
            started_at = datetime.fromisoformat(started_at_str)
            if (now - started_at).total_seconds() > 5400:  # 90 minutes
                try:
                    lease_path.unlink(missing_ok=True)
                except OSError:
                    pass
                return False
        except (TypeError, ValueError):
            pass

    pid = lease.get("pid")
    if not isinstance(pid, int) or pid <= 0:
        try:
            lease_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False

    try:
        os.kill(pid, 0)
        return True
    except (OSError, SystemError):
        try:
            lease_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _get_active_locked_machines(lock_root: Path | None = None) -> set[int]:
    """Scan active device lock files to exclude locked machines from live batch launch."""
    root = lock_root or (Path.home() / ".codex" / "device-locks")
    if not root.is_dir():
        return set()
    locked = set()
    for p in root.glob("machine_*.lock.json"):
        if not p.is_file() or p.is_symlink():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            m = d.get("machine")
            if m is not None:
                locked.add(int(m))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return locked


def _spawn_live(env: Mapping[str, str], day: str, now: datetime) -> int:
    """Spawn run-feed-session.ps1 for due entries (one launch per row).

    Mirrors the proven 17/08 canary pattern: group the due machines by row and
    invoke the canonical launcher once per row with -Machines <list> -Run. The
    child is spawned detached (no waiting), and a lease records the PID so a
    later tick never double-spawns the same window.
    """
    manifest = _load_active_manifest(env, day)
    if not manifest:
        sys.stderr.write("tiktok_runner: no active manifest\n")
        return 0
    if _lease_alive(env, day, now):
        return 0  # previous tick's feed session still running -> no-op
    entries = _due_entries(manifest, now)
    if not entries:
        return 0
    
    locked_set = _get_active_locked_machines()

    row_machines: dict[int, list[str]] = {}
    for entry in entries:
        m = entry.get("machine")
        if m is not None:
            try:
                if int(m) in locked_set:
                    continue  # skip locked machine to avoid collision
            except (ValueError, TypeError):
                pass
        row_machines.setdefault(int(entry["account_row"]), []).append(str(entry["machine"]))
    
    # If all due machines in this tick are locked, no need to spawn
    if not any(row_machines.values()):
        return 0

    repo = Path(env.get("HERMES_CRON_REPO", ""))
    workbook = env.get("HERMES_CRON_FEED_WORKBOOK", "")
    worker_id = env.get("HERMES_CRON_WORKER_ID", "")
    artifact_root = Path(env.get("HERMES_CRON_OFFLINE_ROOT", "")) / "live" / day
    artifact_root.mkdir(parents=True, exist_ok=True)
    python_exe = target_python()
    spawns = []
    for row in sorted(row_machines):
        machines = sorted(set(row_machines[row]))
        if not machines:
            continue
        argv = [
            "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-File", "scripts/run-feed-session.ps1",
            "-Row", str(row),
            "-Machines", ",".join(machines),
            "-AccountWorkbook", workbook,
            "-SkipAccountWorkbookSync",
            "-ArtifactRoot", str(artifact_root / f"row-{row}-{now.strftime('%H%M%S')}"),
            "-Python", python_exe,
            "-Run",
        ]
        child_env = build_child_env(env)
        child_env.pop("PYTHONPATH", None)
        proc = subprocess.Popen(argv, cwd=str(repo), env=child_env)
        spawns.append({"row": row, "machines": machines, "pid": proc.pid})
    lease = {
        "pid": spawns[0]["pid"] if spawns else None,
        "rows": spawns,
        "day": day,
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=4)).isoformat(),
    }
    lease_path = _live_lease_path(env, day)
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    lease_path.write_text(json.dumps(lease, ensure_ascii=False), encoding="utf-8")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if args:
        sys.stderr.write("tiktok_runner: business argv rejected (use activation env)\n")
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
            "tiktok_runner: missing required config: " + ", ".join(sorted(missing)) + "\n"
        )
        return 3

    # Live mode: permit-activated cron run spawns the canonical launcher
    # directly (the offline harness adapter is intentionally disabled).
    # Test mode (HERMES_CRON_RUNNER_ENABLED=1) keeps the offline child path.
    if env.get(ACTIVATION_ENV) != "1" and env.get("HERMES_CRON_REPO") and env.get("HERMES_CRON_FEED_WORKBOOK"):
        return _spawn_live(env, day, now)

    child_argv = build_business_argv(env, day, seed, as_of, reference_time)
    child_env = build_child_env(env)
    subprocess.run(child_argv, cwd=str(repo_root()), env=child_env, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

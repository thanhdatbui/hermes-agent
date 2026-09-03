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
        "HERMES_CRON_ASSIGNMENT_MANIFEST",
        "HERMES_CRON_WORKER_ID",
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


def _active_assignment_manifest_path(env: Mapping[str, str], day: str) -> Path | None:
    pointer = Path(env.get("HERMES_CRON_STATE_ROOT", "")) / "manifests" / day / "ACTIVE.json"
    try:
        if pointer.is_symlink() or not pointer.is_file():
            return None
        data = json.loads(pointer.read_text(encoding="utf-8"))
        manifest_path = Path(data["manifest_path"])
        if not manifest_path.is_absolute():
            manifest_path = pointer.parent / manifest_path
        if manifest_path.is_symlink() or not manifest_path.is_file():
            return None
        return manifest_path
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def _due_entries(manifest: dict, now: datetime) -> list[dict]:
    """Return entries for the active block/session, including late manifests.

    The manifest is a dispatch plan.  Once a session has started, selecting
    only ``slot_time .. slot_time+90m`` drops machines when picker/runner starts
    late and makes the watchdog report a false partial cohort.  Select the
    latest started block/session instead; future sessions remain untouched.
    """
    try:
        repo = str(repo_root())
        if repo not in sys.path:
            sys.path.insert(0, repo)
        from python_runner.hermes_cron.cohort import build_cohort_plan

        plan = build_cohort_plan(manifest, as_of=now.isoformat())
        return [dict(entry) for entry in plan.entries_by_machine.values()]
    except (ImportError, TypeError, ValueError, KeyError):
        # Preserve the wrapper's fail-closed behavior for malformed/legacy
        # manifests: no live spawn is safer than guessing a cohort.
        return []


def _write_cohort_plan(state_root: Path, plan: object) -> None:
    """Persist the frozen expected-machine set before a live spawn."""
    repo = str(repo_root())
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from python_runner.hermes_cron.cohort import CohortPlan

    if not isinstance(plan, CohortPlan):
        raise TypeError("invalid cohort plan")
    path = state_root / "cohorts" / plan.day / f"{plan.cohort_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "cohort_id": plan.cohort_id,
        "day": plan.day,
        "assignment_id": plan.assignment_id,
        "manifest_digest": plan.manifest_digest,
        "block_index": plan.block_index,
        "session_index": plan.session_index,
        "expected_machine_ids": list(plan.expected_machine_ids),
        "expected_count": plan.expected_count,
        "entries_by_machine": {str(machine): dict(entry) for machine, entry in plan.entries_by_machine.items()},
        "started_at": plan.started_at,
        "deadline_at": plan.deadline_at,
        "status": "planned",
    }
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _live_lease_path(env: Mapping[str, str], day: str) -> Path:
    state_root = Path(env.get("HERMES_CRON_STATE_ROOT", ""))
    return state_root / "runner-live-lease" / f"{day}.json"


def _extract_lease_pids(lease: Any) -> list[int]:
    """Extract valid process IDs from a lease dictionary.

    Returns an empty list if any row or PID field is malformed (fail-closed).
    """
    if not isinstance(lease, dict):
        return []
    pids: list[int] = []
    if "rows" in lease:
        rows = lease["rows"]
        if not isinstance(rows, list) or not rows:
            return []
        for r in rows:
            if not isinstance(r, dict):
                return []
            pid = r.get("pid")
            if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
                return []
            pids.append(pid)
        return pids
    pid = lease.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        return []
    return [pid]


def _is_pid_alive(pid: int) -> bool | None:
    """Return True if alive, False if confirmed dead, or None if inaccessible/unknown."""
    if not isinstance(pid, int) or pid <= 0 or pid > 4194304 or isinstance(pid, bool):
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            kernel32 = ctypes.windll.kernel32
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL

            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                err = kernel32.GetLastError()
                # ERROR_INVALID_PARAMETER = 87 (process does not exist)
                if err == 87:
                    return False
                return None
            try:
                exit_code = wintypes.DWORD()
                if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return exit_code.value == STILL_ACTIVE
                return None
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return None
    else:
        try:
            os.kill(pid, 0)
            return True
        except PermissionError:
            return None
        except ProcessLookupError:
            return False
        except (OSError, SystemError, OverflowError):
            return None


def _parse_lease_timestamp(val: Any, fallback_ref: Any = None) -> datetime | None:
    """Parse an ISO timestamp and ensure timezone awareness matches fallback_ref."""
    if not isinstance(val, str) or not val.strip():
        return None
    try:
        dt = datetime.fromisoformat(val)
        if fallback_ref is not None:
            target_tz = getattr(fallback_ref, "tzinfo", fallback_ref)
            if target_tz is not None:
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=target_tz)
            else:
                dt = dt.replace(tzinfo=None)
        else:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def _matches_cohort_exact(raw_tokens: Sequence[str], expected_cohort_id: str) -> bool:
    """Validate that expected_cohort_id matches the argument to -CohortArtifact or --cohort-id."""
    if not expected_cohort_id or not isinstance(expected_cohort_id, str):
        return False
    target_suffix = f"{expected_cohort_id}.json"
    for i, t in enumerate(raw_tokens):
        tl = t.lower()
        if tl in ("-cohortartifact", "/cohortartifact", "--cohort-artifact", "--cohortartifact", "--cohort-id", "--cohort_id") and i + 1 < len(raw_tokens):
            val = raw_tokens[i + 1]
            if val == expected_cohort_id or Path(val).name == target_suffix or Path(val).stem == expected_cohort_id:
                return True
        if tl.startswith(("-cohortartifact=", "/cohortartifact=", "--cohort-artifact=", "--cohortartifact=", "--cohort-id=", "--cohort_id=")):
            val = t.split("=", 1)[1]
            if val == expected_cohort_id or Path(val).name == target_suffix or Path(val).stem == expected_cohort_id:
                return True
    return False


def _is_symlink_or_irregular(path: Path) -> bool:
    """Return True if path is a symlink (including dangling) or non-regular file."""
    try:
        if os.path.islink(str(path)):
            return True
        if path.exists() and not path.is_file():
            return True
    except OSError:
        return True
    return False


def _is_feed_runner_process(pid: int, expected_cohort_id: str | None = None) -> bool:
    """Validate that the PID belongs specifically to a feed-session runner."""
    if _is_pid_alive(pid) is not True:
        return False
    if sys.platform == "win32":
        cmdline = None
        try:
            res = subprocess.run(
                ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:value"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    s = line.strip()
                    if s.lower().startswith("commandline="):
                        cmdline = s[12:].strip()
                        break
        except Exception:
            cmdline = None

        if cmdline is None:
            # Fallback: Query CommandLine via PowerShell CIM
            try:
                ps_cmd = f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine"
                res_ps = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res_ps.returncode == 0 and res_ps.stdout:
                    cmdline = res_ps.stdout.strip()
            except Exception:
                return False

        if not cmdline:
            return False
        try:
            import shlex
            tokens = shlex.split(cmdline, posix=False)
            if not tokens:
                return False
            exe_name = Path(tokens[0].strip('"\'')).name.lower()
            raw_tokens = [t.strip('"\'') for t in tokens]

            if exe_name in ("powershell.exe", "powershell", "pwsh.exe", "pwsh"):
                file_indices = []
                for i, t in enumerate(raw_tokens):
                    tl = t.lower()
                    if tl in ("-file", "/file", "-f", "/f") or tl.startswith("-file:") or tl.startswith("/file:"):
                        file_indices.append(i)
                    elif tl.startswith(("-f", "/f")):
                        file_indices.append(i)
                if len(file_indices) != 1:
                    return False
                first_file_idx = file_indices[0]
                for t in raw_tokens[1:first_file_idx]:
                    tl = t.lower()
                    if tl.startswith(("-c", "/c", "-e", "/e")):
                        return False
                if first_file_idx + 1 >= len(raw_tokens):
                    return False
                target_file = Path(raw_tokens[first_file_idx + 1]).name.lower()
                if target_file != "run-feed-session.ps1":
                    return False
                script_args = raw_tokens[first_file_idx + 2:]
                if expected_cohort_id and not _matches_cohort_exact(script_args, expected_cohort_id):
                    return False
                return True

            if exe_name.startswith("python"):
                i = 1
                script_idx = -1
                while i < len(raw_tokens):
                    t = raw_tokens[i]
                    if t.startswith("-") and not t.startswith("--"):
                        if any(ch in t[1:] for ch in ("c", "m", "C", "M")):
                            return False
                        if t in ("-W", "-X"):
                            i += 2
                            continue
                        i += 1
                        continue
                    if t.startswith("--"):
                        if t == "--check-hash-based-pycs":
                            i += 2
                            continue
                        i += 1
                        continue
                    script_idx = i
                    break
                if script_idx == -1 or Path(raw_tokens[script_idx]).name.lower() != "run_tiktok.py":
                    return False
                script_args = raw_tokens[script_idx + 1:]
                effective_mode = None
                j = 0
                while j < len(script_args):
                    arg = script_args[j]
                    if arg == "--mode" and j + 1 < len(script_args):
                        effective_mode = script_args[j + 1]
                        j += 2
                        continue
                    if arg.startswith("--mode="):
                        effective_mode = arg.split("=", 1)[1]
                    j += 1
                if effective_mode != "multi-machine-feed-session":
                    return False
                if expected_cohort_id and not _matches_cohort_exact(script_args, expected_cohort_id):
                    return False
                return True
            return False
        except Exception:
            return False
    else:
        try:
            cmd_path = Path(f"/proc/{pid}/cmdline")
            if cmd_path.is_file():
                raw = cmd_path.read_bytes()
                parts = [p.decode("utf-8", errors="ignore") for p in raw.split(b"\x00") if p]
            else:
                res = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "args="],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res.returncode != 0 or not res.stdout:
                    return False
                import shlex
                parts = shlex.split(res.stdout.strip())
            if not parts:
                return False
            exe_name = Path(parts[0]).name.lower()
            raw_tokens = list(parts)

            if exe_name in ("powershell", "pwsh", "powershell.exe", "pwsh.exe"):
                file_indices = []
                for i, t in enumerate(raw_tokens):
                    tl = t.lower()
                    if tl in ("-file", "/file", "-f", "/f") or tl.startswith("-file:") or tl.startswith("/file:"):
                        file_indices.append(i)
                    elif tl.startswith(("-f", "/f")):
                        file_indices.append(i)
                if len(file_indices) != 1:
                    return False
                first_file_idx = file_indices[0]
                for t in raw_tokens[1:first_file_idx]:
                    tl = t.lower()
                    if tl.startswith(("-c", "/c", "-e", "/e")):
                        return False
                if first_file_idx + 1 >= len(raw_tokens):
                    return False
                target_file = Path(raw_tokens[first_file_idx + 1]).name.lower()
                if target_file != "run-feed-session.ps1":
                    return False
                script_args = raw_tokens[first_file_idx + 2:]
                if expected_cohort_id and not _matches_cohort_exact(script_args, expected_cohort_id):
                    return False
                return True

            if exe_name.startswith("python"):
                i = 1
                script_idx = -1
                while i < len(raw_tokens):
                    t = raw_tokens[i]
                    if t.startswith("-") and not t.startswith("--"):
                        if any(ch in t[1:] for ch in ("c", "m", "C", "M")):
                            return False
                        if t in ("-W", "-X"):
                            i += 2
                            continue
                        i += 1
                        continue
                    if t.startswith("--"):
                        if t == "--check-hash-based-pycs":
                            i += 2
                            continue
                        i += 1
                        continue
                    script_idx = i
                    break
                if script_idx == -1 or Path(raw_tokens[script_idx]).name.lower() != "run_tiktok.py":
                    return False
                script_args = raw_tokens[script_idx + 1:]
                effective_mode = None
                j = 0
                while j < len(script_args):
                    arg = script_args[j]
                    if arg == "--mode" and j + 1 < len(script_args):
                        effective_mode = script_args[j + 1]
                        j += 2
                        continue
                    if arg.startswith("--mode="):
                        effective_mode = arg.split("=", 1)[1]
                    j += 1
                if effective_mode != "multi-machine-feed-session":
                    return False
                if expected_cohort_id and not _matches_cohort_exact(script_args, expected_cohort_id):
                    return False
                return True
            return False
        except Exception:
            return False


def _kill_stale_pids(pids: Sequence[int], expected_cohort_id: str | None = None) -> bool:
    """Terminate stale or hung batch processes cleanly on Windows/POSIX.

    Validates all live PIDs first (Phase 1). On Windows, acquires open process handles
    prior to validation and holds them throughout termination to completely prevent PID reuse.
    If any live PID fails validation or handle acquisition, aborts immediately without killing.
    """
    if not expected_cohort_id or not isinstance(expected_cohort_id, str) or not expected_cohort_id.strip():
        return False

    valid_live_pids: list[int] = []
    handles: dict[int, Any] = {}

    try:
        for pid in pids:
            if not isinstance(pid, int) or pid <= 0 or pid > 4194304 or isinstance(pid, bool):
                return False
            aliveness = _is_pid_alive(pid)
            if aliveness is False:
                continue
            if aliveness is not True:
                return False

            if sys.platform == "win32":
                try:
                    import ctypes
                    from ctypes import wintypes
                    PROCESS_TERMINATE = 0x0001
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    kernel32 = ctypes.windll.kernel32
                    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                    kernel32.OpenProcess.restype = wintypes.HANDLE
                    h = kernel32.OpenProcess(PROCESS_TERMINATE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                    if h:
                        handles[pid] = h
                except Exception:
                    pass

            if not _is_feed_runner_process(pid, expected_cohort_id=expected_cohort_id):
                return False

            valid_live_pids.append(pid)

        if not valid_live_pids:
            return True

        all_terminated = True
        for pid in valid_live_pids:
            try:
                if sys.platform == "win32":
                    res = subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(pid)],
                        capture_output=True,
                        timeout=10,
                    )
                    if res.returncode not in (0, 128):
                        all_terminated = False
                    h = handles.get(pid)
                    if h:
                        try:
                            kernel32 = ctypes.windll.kernel32
                            kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
                            kernel32.TerminateProcess.restype = wintypes.BOOL
                            kernel32.TerminateProcess(h, 1)
                        except Exception:
                            pass
                else:
                    try:
                        pgid = os.getpgid(pid)
                        if pgid == pid and pgid != os.getpgrp():
                            os.killpg(pgid, 9)
                        else:
                            os.kill(pid, 9)
                    except Exception:
                        os.kill(pid, 9)
            except Exception:
                all_terminated = False

            for _ in range(5):
                if _is_pid_alive(pid) is False:
                    break
                time.sleep(0.1)

            if _is_pid_alive(pid) is not False:
                all_terminated = False

        return all_terminated
    finally:
        if sys.platform == "win32":
            try:
                kernel32 = ctypes.windll.kernel32
                for h in handles.values():
                    kernel32.CloseHandle(h)
            except Exception:
                pass


def _lease_alive(env: Mapping[str, str], day: str, now: datetime) -> bool:
    """Return True when a live spawn from an earlier tick is still running.
    
    If the lease has exceeded a safety threshold (max 90 minutes for a feed session)
    or its recorded process is dead/hung, cleanly clean up the stale lease so
    subsequent cron shifts are never blocked indefinitely.
    """
    lease_path = _live_lease_path(env, day)
    try:
        if _is_symlink_or_irregular(lease_path):
            sys.stderr.write("tiktok_runner: irregular or symlink lease file detected\n")
            return True
        if not lease_path.exists():
            return False
        content = lease_path.read_text(encoding="utf-8").strip()
        if not content:
            sys.stderr.write("tiktok_runner: empty lease file detected\n")
            return True
        lease = json.loads(content)
        if not isinstance(lease, dict):
            sys.stderr.write("tiktok_runner: corrupted existing lease (non-dict)\n")
            return True
    except (OSError, ValueError, json.JSONDecodeError):
        sys.stderr.write("tiktok_runner: error reading existing lease file\n")
        return True

    # Upfront validation of all temporal fields in lease
    expires_at = None
    if "expires_at" in lease:
        expires_at = _parse_lease_timestamp(lease["expires_at"], now.tzinfo)
        if expires_at is None:
            sys.stderr.write("tiktok_runner: corrupted expires_at timestamp in lease\n")
            return True

    started_at = None
    if "started_at" in lease:
        started_at = _parse_lease_timestamp(lease["started_at"], now.tzinfo)
        if started_at is None:
            sys.stderr.write("tiktok_runner: corrupted started_at timestamp in lease\n")
            return True

    pids = _extract_lease_pids(lease)
    if not pids:
        sys.stderr.write("tiktok_runner: lease missing valid PID specifications\n")
        return True

    cohort_id = lease.get("cohort_id")
    if not isinstance(cohort_id, str) or not cohort_id.strip():
        sys.stderr.write("tiktok_runner: lease missing valid cohort_id specification\n")
        return True

    # Guard 1: Hard expiry check
    if expires_at is not None and expires_at < now:
        if _kill_stale_pids(pids, expected_cohort_id=cohort_id):
            try:
                lease_path.unlink()
                return False
            except OSError:
                sys.stderr.write("tiktok_runner: unable to unlink expired lease file\n")
                return True
        return True

    # Guard 2: Max runtime limit for a single feed batch (90 minutes)
    if started_at is not None and (now - started_at).total_seconds() > 5400:
        if _kill_stale_pids(pids, expected_cohort_id=cohort_id):
            try:
                lease_path.unlink()
                return False
            except OSError:
                sys.stderr.write("tiktok_runner: unable to unlink timed-out lease file\n")
                return True
        return True

    alive = any(_is_pid_alive(pid) is not False for pid in pids)
    if alive:
        # Keep the lease while any row child remains alive. This prevents a
        # later tick from duplicating surviving rows when another row exits.
        return True
    try:
        lease_path.unlink()
    except OSError:
        sys.stderr.write("tiktok_runner: unable to unlink dead lease file\n")
        return True
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


def _terminal_cohort_machines(
    env: Mapping[str, str],
    plan: object,
    *,
    as_of: datetime | None = None,
) -> set[int]:
    """Return machines already terminal for this exact immutable cohort."""
    try:
        repo_path = str(repo_root())
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)
        from python_runner.hermes_cron.cohort_watchdog import collect_publications

        # collect_publications appends the logical day itself. Never inspect a
        # relative/empty root: evidence must come from the configured runtime.
        offline_root = Path(env.get("HERMES_CRON_OFFLINE_ROOT", ""))
        if not env.get("HERMES_CRON_OFFLINE_ROOT") or not offline_root.is_absolute():
            return set()
        live_root = offline_root / "live"
        published = set(collect_publications(
            live_root,
            plan,
            as_of=as_of.isoformat() if as_of is not None else None,
        ))
        # Keep the dispatch boundary fail-closed if the collector evolves or
        # returns an unexpected machine id.
        return published & set(plan.expected_machine_ids)
    except (ImportError, OSError, TypeError, ValueError, KeyError, json.JSONDecodeError):
        # Evidence errors must not be converted into a false terminal result.
        return set()


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
    try:
        repo_path = str(repo_root())
        if repo_path not in sys.path:
            sys.path.insert(0, repo_path)
        from python_runner.hermes_cron.cohort import build_cohort_plan
        plan = build_cohort_plan(manifest, as_of=now.isoformat())
    except (ImportError, TypeError, ValueError, KeyError):
        sys.stderr.write("tiktok_runner: active manifest has no valid cohort\n")
        return 0
    entries = [dict(entry) for entry in plan.entries_by_machine.values()]
    if not entries:
        return 0

    # Shift Isolation: If a lease exists from an older cohort, terminate its
    # stale processes and replace the lease so the new shift/session is never blocked.
    lease_path = _live_lease_path(env, day)
    try:
        if _is_symlink_or_irregular(lease_path):
            sys.stderr.write("tiktok_runner: non-regular lease file detected in spawn_live\n")
            return 0
        if lease_path.exists():
            content = lease_path.read_text(encoding="utf-8").strip()
            if not content:
                sys.stderr.write("tiktok_runner: empty lease file detected in spawn_live\n")
                return 0
            existing_lease = json.loads(content)
            if not isinstance(existing_lease, dict):
                sys.stderr.write("tiktok_runner: corrupted existing lease (non-dict)\n")
                return 0
            if "expires_at" in existing_lease:
                datetime.fromisoformat(existing_lease["expires_at"])
            if "started_at" in existing_lease:
                datetime.fromisoformat(existing_lease["started_at"])
            cid = existing_lease.get("cohort_id")
            if isinstance(cid, str) and cid.strip() and cid != plan.cohort_id:
                old_pids = _extract_lease_pids(existing_lease)
                if old_pids and _kill_stale_pids(old_pids, expected_cohort_id=cid):
                    try:
                        lease_path.unlink()
                    except OSError:
                        sys.stderr.write("tiktok_runner: unable to unlink old cohort lease\n")
                        return 0
                else:
                    sys.stderr.write("tiktok_runner: surviving older cohort processes prevented shift isolation\n")
                    return 0
    except (ValueError, json.JSONDecodeError, OSError, TypeError):
        sys.stderr.write("tiktok_runner: corrupted or unreadable existing lease file detected\n")
        return 0

    if _lease_alive(env, day, now):
        return 0  # previous tick's feed session for THIS cohort is still running -> no-op

    # A detached launcher may have finished after the previous cron tick lost
    # its lease. Reconcile exact machine publications before dispatching again;
    # this prevents a completed session from being spawned a second time.
    terminal_machines = _terminal_cohort_machines(env, plan, as_of=now)
    if terminal_machines >= set(plan.expected_machine_ids):
        try:
            lease_path.unlink()
        except OSError:
            pass
        return 0

    # A dead/expired lease must not replay machines that already published a
    # terminal result. Keep those machines in the frozen cohort for accounting,
    # but dispatch only the still-missing per-machine targets.
    entries = [
        entry for entry in entries
        if int(entry["machine"]) not in terminal_machines
    ]
    if not entries:
        return 0

    _write_cohort_plan(Path(env["HERMES_CRON_STATE_ROOT"]), plan)
    
    row_machines: dict[int, list[str]] = {}
    for entry in entries:
        # Do not remove locked machines from the frozen cohort. The canonical
        # launcher/child owns the device-lock decision and emits a terminal
        # skipped publication, keeping expected and dispatched sets identical.
        row_machines.setdefault(int(entry["account_row"]), []).append(str(entry["machine"]))
    
    # If all due machines in this tick are locked, no need to spawn
    if not any(row_machines.values()):
        return 0

    repo = Path(env.get("HERMES_CRON_REPO", ""))
    workbook = env.get("HERMES_CRON_FEED_WORKBOOK", "")
    worker_id = env.get("HERMES_CRON_WORKER_ID", "")
    assignment_manifest = env.get("HERMES_CRON_ASSIGNMENT_MANIFEST")
    if assignment_manifest:
        assignment_path = Path(assignment_manifest)
    else:
        assignment_path = _active_assignment_manifest_path(env, day)
    if assignment_path is None or not assignment_path.is_file():
        sys.stderr.write("tiktok_runner: assignment manifest/worker identity is required\n")
        return 0
    assignment_manifest = str(assignment_path)
    if not worker_id:
        sys.stderr.write("tiktok_runner: assignment manifest/worker identity is required\n")
        return 0
    artifact_root = Path(env.get("HERMES_CRON_OFFLINE_ROOT", "")) / "live" / day
    artifact_root.mkdir(parents=True, exist_ok=True)
    python_exe = target_python()

    popen_kwargs: dict[str, Any] = {
        "cwd": str(repo),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = 0x08000200  # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    else:
        popen_kwargs["start_new_session"] = True

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
            "-AccountWorkbook", Path(workbook).as_posix() if workbook else "",
            "-AssignmentManifest", Path(assignment_manifest).as_posix(),
            "-WorkerId", worker_id,
            "-CohortArtifact", (Path(env["HERMES_CRON_STATE_ROOT"]) / "cohorts" / day / f"{plan.cohort_id}.json").as_posix(),
            "-SkipAccountWorkbookSync",
            "-ArtifactRoot", (artifact_root / f"row-{row}-{now.strftime('%H%M%S')}").as_posix(),
            "-Python", python_exe,
            "-Run",
        ]
        child_env = build_child_env(env)
        child_env.pop("PYTHONPATH", None)
        popen_kwargs["env"] = child_env
        proc = subprocess.Popen(argv, **popen_kwargs)
        spawns.append({"row": row, "machines": machines, "pid": proc.pid})
    lease = {
        "pid": spawns[0]["pid"] if spawns else None,
        "rows": spawns,
        "day": day,
        "started_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=4)).isoformat(),
        "cohort_id": plan.cohort_id,
        "expected_machine_ids": list(plan.expected_machine_ids),
        "expected_count": plan.expected_count,
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

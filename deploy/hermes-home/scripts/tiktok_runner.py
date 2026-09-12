"""Simplified Hermes cron wrapper for TikTok feed sessions.

Determines the current hour in HCM timezone, maps it to a Row number
based on even/odd calendar day, deduplicates via a simple state file,
and spawns run-feed-session.ps1 directly against taikhoan_run_safe.xlsx.

No picker / cohort / manifest dependency.
"""

from __future__ import annotations

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

# -- Dynamic Host Config (Kibe vs Admin) ------------------------------------
try:
    if "D:/Taadaa/Tiktok_Reg" not in sys.path:
        sys.path.insert(0, "D:/Taadaa/Tiktok_Reg")
    import taadaa_host as _taadaa_host_mod
    _host_cfg = _taadaa_host_mod.load_host_config()
    _workbook_root = Path(_host_cfg["workbook_root"])
    _runtime_root = Path(_host_cfg["runtime_root"])
except Exception:
    _workbook_root = Path("D:/OneDrive/TaadaaData/kibe")
    _runtime_root = Path("D:/Taadaa/runtime/kibe")

ACCOUNT_WORKBOOK = str(_workbook_root / "taikhoan_run_safe.xlsx")
STATE_DIR = _runtime_root / "cron-state"
STATE_FILE = STATE_DIR / "runner_simple_state.json"
ARTIFACT_BASE = _runtime_root / "live"


# ---------------------------------------------------------------------------
# Schedule: 4 Ca x 2 Phiên / ngày (0h = Ca đầu ngày, không cross-midnight)
#   Ca 1 (Sáng): Phiên 1 lúc 06:00 (Row 1/2), Phiên 2 lúc 08:00 (Row 1/2)
#   Ca 2 (Trưa): Phiên 1 lúc 12:00 (Row 3/4), Phiên 2 lúc 14:00 (Row 3/4)
#   Ca 3 (Tối):  Phiên 1 lúc 18:00 (Row 5/6), Phiên 2 lúc 20:00 (Row 5/6)
#   Ca 4 (Đêm):  Phiên 1 lúc 00:00 (Row 7/8), Phiên 2 lúc 01:30 (Row 7/8)
#
#   Day EVEN (date % 2 == 0): Row chẵn (Row 8, 2, 4, 6)
#   Day ODD  (date % 2 == 1): Row lẻ   (Row 7, 1, 3, 5)
# ---------------------------------------------------------------------------

_SCHEDULE: dict[tuple[int, int], dict[int, int]] = {
    # (hour, minute) -> {day_parity (0=even, 1=odd) -> row}
    (0, 0):   {0: 8, 1: 7},   # Ca 4 Phiên 1
    (1, 30):  {0: 8, 1: 7},   # Ca 4 Phiên 2
    (6, 0):   {0: 2, 1: 1},   # Ca 1 Phiên 1
    (8, 0):   {0: 2, 1: 1},   # Ca 1 Phiên 2
    (12, 0):  {0: 4, 1: 3},   # Ca 2 Phiên 1
    (14, 0):  {0: 4, 1: 3},   # Ca 2 Phiên 2
    (18, 0):  {0: 6, 1: 5},   # Ca 3 Phiên 1
    (20, 0):  {0: 6, 1: 5},   # Ca 3 Phiên 2
}


def _determine_row(now: datetime) -> tuple[int, int, str] | None:
    """Return (row, session_index, window_key) or None if dead-zone / unmapped time window.

    Session 1: 00:00, 06:00, 12:00, 18:00 (Feed only)
    Session 2: 01:30, 08:00, 14:00, 20:00 (Feed + Upload hook)
    """
    hour = now.hour
    minute = now.minute

    # Dead zone: 02:30 -> 05:59
    if (hour == 2 and minute >= 30) or (3 <= hour <= 5):
        return None

    # Match exact or nearest window slot
    slot_key: tuple[int, int] | None = None
    window_suffix: str = ""

    if hour == 0:
        slot_key = (0, 0)
        window_suffix = "00"
    elif hour == 1:
        if minute >= 30:
            slot_key = (1, 30)
            window_suffix = "0130"
        else:
            return None
    elif hour == 2:
        # Từ 02:00 đến 02:29 vẫn thuộc window 01:30 nếu cron trễ
        slot_key = (1, 30)
        window_suffix = "0130"
    elif hour == 6:
        slot_key = (6, 0)
        window_suffix = "06"
    elif hour == 8:
        slot_key = (8, 0)
        window_suffix = "08"
    elif hour == 12:
        slot_key = (12, 0)
        window_suffix = "12"
    elif hour == 14:
        slot_key = (14, 0)
        window_suffix = "14"
    elif hour == 18:
        slot_key = (18, 0)
        window_suffix = "18"
    elif hour == 20:
        slot_key = (20, 0)
        window_suffix = "20"
    else:
        return None

    slots = _SCHEDULE.get(slot_key)
    if slots is None:
        return None

    session_index = 2 if slot_key in ((1, 30), (8, 0), (14, 0), (20, 0)) else 1
    parity = now.date().day % 2  # 0 = even, 1 = odd
    row = slots[parity]
    window_key = f"{now.date().isoformat()}T{window_suffix}"
    return row, session_index, window_key


# ---------------------------------------------------------------------------
# Helpers kept from original wrapper
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    """Resolve the repository root (pinned env wins, then walk up to .git)."""
    pinned = os.environ.get("HERMES_CRON_REPO")
    if pinned:
        candidate = Path(pinned)
        if (candidate / ".git").is_dir() or (candidate / ".git").is_file():
            return candidate
    for root in ("D:/Taadaa/tiktok-luot nuoi acc",):
        candidate = Path(root)
        if (candidate / ".git").is_dir() or (candidate / ".git").is_file():
            return candidate
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
    return here.parents[1]


def target_python() -> str:
    """Resolve the target Python as a Windows path (CreateProcess-safe)."""
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
    return repo_root() / "runtime" / "hermes-cron" / "permits" / f"{Path(__file__).stem}.permit"


def repo_env_overrides() -> dict[str, str]:
    """Repo-anchored env fallback for a cron run (kept for backwards compat)."""
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
    merged = dict(env)
    for key, value in repo_env_overrides().items():
        merged.setdefault(key, value)
    return merged


# ---------------------------------------------------------------------------
# State de-dup
# ---------------------------------------------------------------------------

def _load_state() -> dict:
    try:
        if STATE_FILE.is_file() and not STATE_FILE.is_symlink():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return {}


def _save_state(row: int, window_key: str, now: datetime) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_row": row,
        "last_window": window_key,
        "last_run_at": now.isoformat(),
    }
    tmp = STATE_FILE.parent / f".runner_simple_state.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(STATE_FILE))


def _already_ran(window_key: str) -> bool:
    state = _load_state()
    return state.get("last_window") == window_key


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def _preflight_ensure_accounts(row: int) -> None:
    """Check va tu dong reg bu tai khoan neu Row do co may bi trong."""
    ensure_script = Path(r"D:\Taadaa\tools\ensure_row_accounts.py")
    if not ensure_script.is_file():
        return
    try:
        sys.stdout.write(f"tiktok_runner: preflight checking accounts for Row {row}...\n")
        sys.stdout.flush()
        subprocess.run(
            [sys.executable, str(ensure_script), str(row)],
            check=False,
            timeout=5400,
        )
    except Exception as exc:
        sys.stderr.write(f"tiktok_runner: preflight ensure_row_accounts error: {exc}\n")


# ---------------------------------------------------------------------------
# Spawn
# ---------------------------------------------------------------------------

def _spawn_feed_session(row: int, session_index: int, now: datetime) -> int:
    """Spawn run-feed-session.ps1 for the given Row and SessionIndex."""
    repo = repo_root()
    ps1_path = repo / "scripts" / "run-feed-session.ps1"
    if not ps1_path.is_file():
        sys.stderr.write(f"tiktok_runner: PS1 not found at {ps1_path}\n")
        return 3

    ps1_win = str(ps1_path).replace("/", "\\")

    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    artifact_root = str(ARTIFACT_BASE / date_str / f"row-{row}-{time_str}").replace("/", "\\")

    argv = [
        "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", ps1_win,
        "-Python", target_python(),
        "-Row", str(row),
        "-SessionIndex", str(session_index),
        "-AllowUploadHook",
        "-Preset", "full",
        "-AccountWorkbook", ACCOUNT_WORKBOOK.replace("/", "\\"),
        "-ArtifactRoot", artifact_root,
        "-SkipAccountWorkbookSync",
        "-LocalRun",
        "-MachineStartStaggerMs", "2000,8000",
        "-RandomizeMachineOrder",
        "-Run",
    ]

    kwargs: dict = {
        "cwd": str(repo),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000200  # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(argv, **kwargs)
    sys.stdout.write(
        f"tiktok_runner: spawned Row{row} pid={proc.pid}\n"
    )
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if args:
        sys.stderr.write("tiktok_runner: no arguments accepted (use activation env)\n")
        return 2

    env = merged_env(os.environ)
    if not is_activated(env):
        return 0

    now = now_hcmc()

    result = _determine_row(now)
    if result is None:
        return 0

    row, session_index, window_key = result

    if _already_ran(window_key):
        return 0

    _preflight_ensure_accounts(row)

    rc = _spawn_feed_session(row, session_index, now)
    if rc == 0:
        _save_state(row, window_key, now)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())

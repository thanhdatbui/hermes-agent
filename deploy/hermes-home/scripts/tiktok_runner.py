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
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

TARGET_PYTHON_DEFAULT = "/d/Taadaa/python-envs/automation/Scripts/python.exe"
TARGET_PYTHON_ENV = "HERMES_CRON_TARGET_PYTHON"
NOW_ENV = "HERMES_CRON_NOW"

ACTIVATION_ENV = "HERMES_CRON_RUNNER_ENABLED"
PERMIT_ENV = "HERMES_CRON_PERMIT_FILE"

# -- Dual-Cluster Workbooks & Roots (Kibe + Admin) ---------------------------
KIBE_WORKBOOK_ROOT = Path("D:/OneDrive/TaadaaData/kibe")
ADMIN_WORKBOOK_ROOT = Path("D:/OneDrive/TaadaaData/admin")

KIBE_RUNTIME_ROOT = Path("D:/Taadaa/runtime/kibe")
ADMIN_RUNTIME_ROOT = Path("D:/Taadaa/runtime/admin")

CLUSTERS: list[dict[str, Any]] = [
    {
        "name": "kibe",
        "workbook_root": KIBE_WORKBOOK_ROOT,
        "runtime_root": KIBE_RUNTIME_ROOT,
        "account_workbook": str(KIBE_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx"),
        "state_file": KIBE_RUNTIME_ROOT / "cron-state" / "runner_simple_state.json",
        "artifact_base": KIBE_RUNTIME_ROOT / "live",
        "host_config": r"D:\Taadaa\machine-config\kibe.yaml",
        "adb_server_socket": None,
    },
    {
        "name": "admin",
        "workbook_root": ADMIN_WORKBOOK_ROOT,
        "runtime_root": ADMIN_RUNTIME_ROOT,
        "account_workbook": str(ADMIN_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx"),
        "state_file": ADMIN_RUNTIME_ROOT / "cron-state" / "runner_simple_state.json",
        "artifact_base": ADMIN_RUNTIME_ROOT / "live",
        "host_config": r"D:\Taadaa\machine-config\admin.yaml",
        "adb_server_socket": "tcp:192.168.110.119:5037",
    },
]

# Legacy backward-compatibility aliases
ACCOUNT_WORKBOOK = str(KIBE_WORKBOOK_ROOT / "taikhoan_run_safe.xlsx")
STATE_DIR = KIBE_RUNTIME_ROOT / "cron-state"
STATE_FILE = STATE_DIR / "runner_simple_state.json"
ARTIFACT_BASE = KIBE_RUNTIME_ROOT / "live"


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
    # Chu kỳ xoay tua 6 ngày cân bằng farm (4 acc/ngày + ngày dưỡng sinh rửa trust):
    # Day 0, 4: Row lẻ (7, 1, 3, 5) - Cày Follow + Up
    # Day 1, 3: Row chẵn (8, 2, 4, 6) - Cày Follow + Up
    # Day 2: Row lẻ (7, 1, 3, 5) - DƯỠNG SINH RỬA TRUST (CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP)
    # Day 5: Row chẵn (8, 2, 4, 6) - DƯỠNG SINH RỬA TRUST (CHỈ LƯỚT FEED, 0 FOLLOW, KHÔNG UP)
    # Phân định lịch Chẵn / Lẻ theo ngày dương lịch (1 = row lẻ, 0 = row chẵn)
    # Từng nick sẽ tự xác định ngày dưỡng sinh độc lập (1/3 organic rest) tại worker
    parity = 0 if (now.day % 2 == 0) else 1
    row = slots[parity]
    is_rest_day = False
    window_key = f"{now.date().isoformat()}T{window_suffix}"
    return row, session_index, window_key, is_rest_day


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

def _load_state(state_file: Path = STATE_FILE) -> dict:
    try:
        if state_file.is_file() and not state_file.is_symlink():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, ValueError, json.JSONDecodeError):
        pass
    return {}


def _save_state(row: int, window_key: str, now: datetime, state_file: Path = STATE_FILE) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_row": row,
        "last_window": window_key,
        "last_run_at": now.isoformat(),
    }
    tmp = state_file.parent / f".runner_simple_state.{os.getpid()}.tmp"
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(state_file))


def _already_ran(window_key: str, state_file: Path = STATE_FILE) -> bool:
    state = _load_state(state_file)
    return state.get("last_window") == window_key


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

def _preflight_ensure_accounts(row: int, window_key: str, cluster: dict[str, Any] | None = None) -> None:
    """Check và tự động reg bù tài khoản nếu Row bị trống (hỗ trợ cả Kibe và Admin).
    Dùng marker file .preflight_<cluster>_<window_key> để chỉ chạy đúng 1 lần duy nhất mỗi window, chống spam loop 15 phút.
    """
    cluster = cluster or CLUSTERS[0]
    cluster_name = cluster.get("name", "kibe")
    state_file = cluster.get("state_file")
    cluster_state_dir = Path(state_file).parent if state_file else STATE_DIR
    cluster_state_dir.mkdir(parents=True, exist_ok=True)

    marker = cluster_state_dir / f".preflight_{cluster_name}_{window_key}"
    if marker.exists():
        sys.stdout.write(f"tiktok_runner [{cluster_name}]: preflight already executed for window {window_key}, skipping.\n")
        return

    ensure_script = Path(r"D:\Taadaa\tools\ensure_row_accounts.py")
    if not ensure_script.is_file():
        return

    try:
        marker.write_text(datetime.now().isoformat(), encoding="utf-8")
        sys.stdout.write(f"tiktok_runner [{cluster_name}]: preflight checking accounts for Row {row} (window {window_key})...\n")
        sys.stdout.flush()

        child_env = dict(os.environ)
        if cluster.get("host_config"):
            child_env["TAADAA_HOST_CONFIG"] = cluster["host_config"]
        if cluster.get("adb_server_socket"):
            child_env["ADB_SERVER_SOCKET"] = cluster["adb_server_socket"]

        subprocess.run(
            [target_python(), str(ensure_script), str(row)],
            check=False,
            timeout=5400,
            env=child_env,
        )
    except Exception as exc:
        sys.stderr.write(f"tiktok_runner [{cluster_name}]: preflight ensure_row_accounts error: {exc}\n")


def _count_valid_accounts_for_row(row: int, workbook_path: str = ACCOUNT_WORKBOOK) -> int:
    """Đếm số account hợp lệ cho row trong workbook chỉ định."""
    safe_path = Path(workbook_path)
    if not safe_path.is_file():
        sys.stderr.write(f"tiktok_runner: Safe workbook khong ton tai: {safe_path}\n")
        return 0
    try:
        import openpyxl
        wb = openpyxl.load_workbook(safe_path, read_only=True)
        ws = wb.active
        machine_slots: dict[int, list[object]] = {}
        for r in ws.iter_rows(min_row=2, values_only=True):
            if not r or r[0] is None:
                continue
            try:
                m_num = int(str(r[0]).strip())
            except ValueError:
                continue
            machine_slots.setdefault(m_num, []).append(r[2] if len(r) > 2 else None)
        slot_idx = row - 1
        valid = 0
        for m, slots in machine_slots.items():
            if slot_idx < len(slots):
                val = slots[slot_idx]
                if val and str(val).strip() and str(val).strip().lower() != "none":
                    valid += 1
        return valid
    except Exception as exc:
        sys.stderr.write(f"tiktok_runner: error reading safe workbook: {exc}\n")
        return 0


# ---------------------------------------------------------------------------
# Spawn
# ---------------------------------------------------------------------------

def _spawn_feed_session(
    row: int,
    session_index: int,
    now: datetime,
    is_rest_day: bool = False,
    account_workbook: str = ACCOUNT_WORKBOOK,
    artifact_base: Path = ARTIFACT_BASE,
    host_config: str | None = None,
    adb_server_socket: str | None = None,
) -> int:
    """Spawn run-feed-session.ps1 for the given Row and SessionIndex."""
    repo = repo_root()
    ps1_path = repo / "scripts" / "run-feed-session.ps1"
    if not ps1_path.is_file():
        sys.stderr.write(f"tiktok_runner: PS1 not found at {ps1_path}\n")
        return 3

    ps1_win = str(ps1_path).replace("/", "\\")

    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    artifact_root = str(artifact_base / date_str / f"row-{row}-{time_str}").replace("/", "\\")

    argv = [
        "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
        "-File", ps1_win,
        "-Python", target_python(),
        "-Row", str(row),
        "-SessionIndex", str(session_index),
        # Cơ chế cơ hội (Opportunistic Upload): Cho phép upload ở cả Phiên 1 & Phiên 2 khi KHÔNG phải ngày dưỡng sinh.
        # Hệ thống có sổ cái shift_upload_history.json tự động chặn nếu phiên trước đã đăng thành công.
        *( ["-AllowUploadHook"] if not is_rest_day else [] ),
        "-Preset", "full",
        "-AccountWorkbook", account_workbook.replace("/", "\\"),
        "-ArtifactRoot", artifact_root,
        "-SkipAccountWorkbookSync",
        "-LocalRun",
        "-MachineStartStaggerMs", "2000,8000",
        "-RandomizeMachineOrder",
        "-Run",
    ]

    child_env = dict(os.environ)
    child_env.pop("TAADAA_REST_DAY_NO_FOLLOW", None)
    if host_config:
        child_env["TAADAA_HOST_CONFIG"] = host_config
    if adb_server_socket:
        child_env["ADB_SERVER_SOCKET"] = adb_server_socket
    else:
        child_env.pop("ADB_SERVER_SOCKET", None)
    kwargs: dict = {
        "cwd": str(repo),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
        "env": child_env,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000200  # CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True

    proc = subprocess.Popen(argv, **kwargs)
    sys.stdout.write(
        f"tiktok_runner: spawned Row{row} pid={proc.pid} [host={host_config} socket={adb_server_socket}]\n"
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

    row, session_index, window_key, is_rest_day = result

    # Chạy tuần tự qua các cụm Farm (Kibe Local + Admin Remote)
    overall_rc = 0
    rest_tag = " [REST DAY - PURE FEED]" if is_rest_day else ""

    for cluster in CLUSTERS:
        cluster_name = cluster["name"]
        cluster_wb = cluster["account_workbook"]
        cluster_state = cluster["state_file"]
        cluster_artifact = cluster["artifact_base"]

        if _already_ran(window_key, state_file=cluster_state):
            continue

        _preflight_ensure_accounts(row, window_key, cluster=cluster)

        valid_count = _count_valid_accounts_for_row(row, workbook_path=cluster_wb)
        if valid_count == 0:
            sys.stdout.write(
                f"tiktok_runner [{cluster_name}]: Row {row} co 0 account hop le trong {cluster_wb}, skipping window {window_key}.\n"
            )
            _save_state(row, window_key, now, state_file=cluster_state)
            continue

        sys.stdout.write(
            f"tiktok_runner [{cluster_name}]: Row {row} co {valid_count} accounts hop le{rest_tag}.\n"
        )

        cluster_host_cfg = cluster.get("host_config")
        cluster_adb_socket = cluster.get("adb_server_socket")
        rc = _spawn_feed_session(
            row,
            session_index,
            now,
            is_rest_day=is_rest_day,
            account_workbook=cluster_wb,
            artifact_base=cluster_artifact,
            host_config=cluster_host_cfg,
            adb_server_socket=cluster_adb_socket,
        )
        if rc == 0:
            _save_state(row, window_key, now, state_file=cluster_state)
        else:
            overall_rc = rc

    return overall_rc


if __name__ == "__main__":
    raise SystemExit(main())

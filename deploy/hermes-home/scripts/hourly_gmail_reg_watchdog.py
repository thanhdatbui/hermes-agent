#!/usr/bin/env python3
"""Hourly, silent Gmail-registration watchdog for the two phone farms.

The module keeps its decision logic side-effect free where possible so it can be
unit-tested without access to the farm.  The cron entry point emits no stdout;
only the explicit report path sends a Telegram summary.
"""
# === Step 1: Architecture and Imports ===
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Mapping, Sequence

BLOCKED_WINDOWS = (
    ("dọn cache", (4, 0), (4, 30)),
    ("ca nuôi sáng", (5, 5), (9, 30)),
    ("đệm ca trưa", (11, 5), (11, 35)),
    ("ca nuôi trưa", (11, 45), (15, 30)),
    ("đệm ca chiều", (17, 5), (17, 35)),
    ("ca nuôi chiều", (17, 45), (21, 30)),
)
CRON_SCHEDULE = "0 * * * *"

FARMS = ("Kibe", "Admin")
DAILY_CAP = 20
COOLDOWN_DAYS = 4
GMAIL_REPORT_CHAT_ID = "-5139245637"
FARM_MASTER_DB = Path(r"D:\Taadaa\data\farm_master.db")
GPM_DB_PATH = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
LOCK_DIR = Path(r"C:\Users\Kibe\AppData\Local\automation-core\device-locks")
CODEX_LOCK_DIR = Path(r"C:\Users\Kibe\.codex\device-locks")
STATE_FILE = Path(r"D:\Taadaa\runtime\kibe\cron-state\hourly_gmail_reg_state.json")
GMAIL_REPO_DIR = Path(r"D:\Taadaa\register gmail")
GMAIL_SCRIPT = GMAIL_REPO_DIR / "gmail_reg_v10.py"
AUTOMATION_CORE_SRC = Path(r"D:\Taadaa\automation-core\src")
PYTHON_EXE = Path(r"D:\Taadaa\python-envs\automation\Scripts\python.exe")
ADMIN_SSH = Path(r"D:\Taadaa\tools\admin_ssh.py")


def now_local() -> datetime:
    return datetime.now().astimezone().replace(tzinfo=None)


def _minutes(value: tuple[int, int]) -> int:
    return value[0] * 60 + value[1]


def is_safe_window(when: datetime | None = None) -> bool:
    """Return false when ``when`` falls inclusively inside a blocked window."""
    when = when or now_local()
    minute = when.hour * 60 + when.minute
    return not any(_minutes(start) <= minute <= _minutes(end) for _, start, end in BLOCKED_WINDOWS)


def _proxy_host_port(endpoint: object) -> str:
    text = str(endpoint or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"^[a-z][a-z0-9+.-]*://", "", text)
    text = text.rsplit("@", 1)[-1].split("/", 1)[0]
    return text


def is_machine_idle(machine_id: int | str, *, lock_dirs: Sequence[Path] = (LOCK_DIR, CODEX_LOCK_DIR), next_slot_gap: float = 9999.0) -> bool:
    """A machine is idle only without any lock and with >=45 minutes of slack."""
    if next_slot_gap < 45:
        return False
    needle = str(machine_id)
    for directory in lock_dirs:
        if not directory.is_dir():
            continue
        for path in directory.glob("*.lock.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
            names = {str(data.get(k, "")) for k in ("machine_id", "machine", "mid", "device_id")}
            if needle in names or needle in path.stem:
                return False
        if any(directory.glob("*.lock")):
            return False
    return True


def _machine_number(machine_id: object) -> int | None:
    match = re.search(r"\d+", str(machine_id or ""))
    return int(match.group()) if match else None


def p0_machine_ids(gpm_db: Path = GPM_DB_PATH) -> set[int]:
    """Machine numbers represented by P0 / priority-maintenance GPM profiles."""
    if not gpm_db.exists():
        return set()
    try:
        with sqlite3.connect(gpm_db) as conn:
            has_groups = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='Groups'").fetchone()
            if has_groups:
                rows = conn.execute(
                    "SELECT p.Name FROM Profiles p JOIN Groups g ON p.GroupId = g.Id "
                    "WHERE lower(g.Name) IN ('p0', 'priority', 'needs-login')"
                ).fetchall()
            else:
                rows = conn.execute("SELECT Name FROM Profiles WHERE GroupId = 1").fetchall()
    except sqlite3.Error:
        return set()
    return {number for (name,) in rows if (number := _machine_number(name)) is not None}


def _latest_gmail_reg(conn: sqlite3.Connection, machine_id: object) -> str | None:
    try:
        row = conn.execute(
            "SELECT MAX(created_at) FROM mailboxes "
            "WHERE lower(email) LIKE '%@gmail.com' AND machine_id = ?",
            (machine_id,),
        ).fetchone()
    except sqlite3.Error:
        return None
    return row[0] if row else None


def _parse_time(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def load_candidates(db_path: Path = FARM_MASTER_DB, *, now: datetime | None = None, p0_machine_ids: set[int] | None = None, idle_checker=is_machine_idle) -> list[dict]:
    """Read SSOT machines and return cooldown, P0, idle and proxy-eligible rows."""
    now = now or now_local()
    blocked_p0_ids = p0_machine_ids if p0_machine_ids is not None else globals()["p0_machine_ids"]()
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(db_path)
        machine_rows = conn.execute("SELECT machine_id, owner, proxy_endpoint FROM machines").fetchall()
    except sqlite3.Error:
        return []
    results = []
    try:
        for machine_id, owner, proxy_endpoint in machine_rows:
            farm = "Admin" if str(owner).strip().lower() == "admin" else "Kibe"
            mid = _machine_number(machine_id)
            if mid in blocked_p0_ids:
                continue
            latest = _parse_time(_latest_gmail_reg(conn, machine_id))
            if latest is not None and now - latest < timedelta(days=COOLDOWN_DAYS):
                continue
            if not idle_checker(machine_id):
                continue
            results.append({"machine_id": mid if mid is not None else machine_id, "farm": farm, "proxy_endpoint": proxy_endpoint or "", "last_reg_at": latest.isoformat() if latest else None})
    finally:
        conn.close()
    return results


def select_distinct_proxy_candidates(candidates: Iterable[Mapping], *, per_farm: int = 2) -> list[dict]:
    selected: list[dict] = []
    counts = {farm: 0 for farm in FARMS}
    proxies = {farm: set() for farm in FARMS}
    for candidate in candidates:
        farm = str(candidate.get("farm", "Kibe"))
        if farm not in counts or counts[farm] >= per_farm:
            continue
        proxy = _proxy_host_port(candidate.get("proxy_endpoint"))
        if proxy in proxies[farm]:
            continue
        item = dict(candidate)
        item["proxy_key"] = proxy
        selected.append(item)
        counts[farm] += 1
        proxies[farm].add(proxy)
    return selected


def _read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"runs": []}


def _runs_today(state: Mapping, when: datetime) -> dict[str, int]:
    counts = {farm: 0 for farm in FARMS}
    for run in state.get("runs", []):
        timestamp = _parse_time(run.get("timestamp"))
        if timestamp and timestamp.date() == when.date() and run.get("farm") in counts:
            counts[run["farm"]] += 1
    return counts


def format_daily_report(state: Mapping, *, now: datetime | None = None) -> str:
    now = now or now_local()
    since = now - timedelta(hours=24)
    rows = [r for r in state.get("runs", []) if (ts := _parse_time(r.get("timestamp"))) and ts >= since]
    lines = ["### BÁO CÁO GMAIL REG 24H ###"]
    for farm in FARMS:
        farm_rows = [r for r in rows if r.get("farm") == farm]
        success = sum(r.get("status") == "success" for r in farm_rows)
        failed = sum(r.get("status") == "failed" for r in farm_rows)
        lines.append(f"{farm}: Tổng {len(farm_rows)} | Thành công: {success} | Thất bại: {failed}")
    return "\n".join(lines)


def _send_telegram_text(chat_id: str, text: str) -> None:
    try:
        from automation_core.alerts import _send_telegram_text as sender, _load_bot_token
    except ImportError:
        return
    token = _load_bot_token()
    if token:
        sender(token, chat_id, text)


def _run_registration(candidate: Mapping) -> tuple[str, int]:
    mid = str(candidate["machine_id"])
    farm = candidate["farm"]
    if farm == "Kibe":
        env = dict(os.environ)
        env["PYTHONPATH"] = str(AUTOMATION_CORE_SRC) + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run([str(PYTHON_EXE if PYTHON_EXE.exists() else Path(sys.executable)), str(GMAIL_SCRIPT), mid, "--ss"], cwd=GMAIL_REPO_DIR, env=env, capture_output=True, text=True, timeout=420)
    else:
        command = f"Set-Location 'D:\\Taadaa\\register gmail'; & 'D:\\Taadaa\\python-envs\\automation\\Scripts\\python.exe' 'D:\\Taadaa\\register gmail\\gmail_reg_v10.py' {mid} --ss"
        proc = subprocess.run([str(Path(sys.executable)), str(ADMIN_SSH), "--timeout", "420", "--powershell", command], capture_output=True, text=True, timeout=420)
    return ("success" if proc.returncode == 0 else "failed"), proc.returncode


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, STATE_FILE)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    current = now_local()
    state = _read_state()
    if args.report_only or args.force or current.hour == 8:
        _send_telegram_text(GMAIL_REPORT_CHAT_ID, format_daily_report(state, now=current))
        if args.report_only:
            return 0
    if not args.force and not is_safe_window(current):
        return 0
    if is_feed_runner_active():
        return 0
    counts = _runs_today(state, current)
    if all(counts[farm] >= DAILY_CAP for farm in FARMS):
        return 0
    candidates = select_distinct_proxy_candidates(load_candidates(), per_farm=2)
    for candidate in candidates:
        farm = candidate["farm"]
        if counts[farm] >= DAILY_CAP:
            continue
        try:
            status, code = _run_registration(candidate)
        except Exception:
            status, code = "failed", 1
        state.setdefault("runs", []).append({"timestamp": current.isoformat(), "farm": farm, "machine_id": candidate["machine_id"], "status": status, "exit_code": code})
        # The cap is a machine-attempt cap, not a success cap.
        counts[farm] += 1
    _save_state(state)
    return 0


def is_feed_runner_active() -> bool:
    try:
        import psutil
        needles = ("tiktok_runner", "feed_session", "run_post")
        for process in psutil.process_iter(["cmdline", "name"]):
            command = " ".join(process.info.get("cmdline") or []).lower()
            if any(needle in command for needle in needles):
                return True
    except Exception:
        return False
    return False


if __name__ == "__main__":
    raise SystemExit(main())

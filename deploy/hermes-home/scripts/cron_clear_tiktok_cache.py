# -*- coding: utf-8 -*-
"""Cron task: Clear TikTok cache at the end of the shift/day across connected machines.

Uses UI Deep Link intent or UI widget on Home screen via ADB.
STRICTLY FORBIDS `pm clear` or any system data wipe.
Runs concurrently in batches to finish within minutes across the farm.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add automation-core src to sys.path for DeviceLock and alerts
sys.path.insert(0, r"D:\Taadaa\automation-core\src")
try:
    from automation_core.device_lock import DeviceLock, DeviceLockUnavailable, DeviceLockNeedsUserDecision
except ImportError:
    DeviceLock = None
    DeviceLockUnavailable = Exception
    DeviceLockNeedsUserDecision = Exception

ADB = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
DEFAULT_WIDGET_POS = (810, 260)
TIK1_WORKBOOK = r"D:\OneDrive\TaadaaData\kibe\Tik1.xlsx"
SCRIPT_PATH = r"D:\Taadaa\automation-core\scripts\clear-tiktok-cache.py"
MAX_WORKERS = 20
WIN_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}

STATE_FILE = Path("D:/Taadaa/runtime/kibe/cron-state/post_night_clear_cache_state.json")
REPORTED_FILE = Path("D:/Taadaa/runtime/kibe/cron-state/feed_session_reported.json")


def is_feed_runner_active() -> bool:
    """Check if feed runner or runner processes are currently active."""
    target_procs = {
        "multi_machine_feed_session",
        "run_tiktok.py",
        "tiktok_runner.py",
        "hermes_cron_runner.py",
    }
    try:
        import psutil
        for p in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                cmdline = p.info.get("cmdline") or []
                cmd_str = " ".join(cmdline).lower()
                for target in target_procs:
                    if target.lower() in cmd_str:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as exc:
        sys.stderr.write(f"[WARN] Failed to check running processes via psutil: {exc}\n")
    return False


def get_connected_devices() -> dict[str, str]:
    """Map serial -> device state."""
    for attempt in range(2):
        try:
            proc = subprocess.run([ADB, "devices"], capture_output=True, text=True, timeout=15, **WIN_KWARGS)
            lines = proc.stdout.strip().splitlines()[1:]
            devices = {}
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices[parts[0]] = parts[1]
            return devices
        except Exception as exc:
            if attempt == 0:
                time.sleep(2)
                continue
            sys.stderr.write(f"[WARN] Failed to get adb devices: {exc}\n")
            return {}
    return {}


def load_machine_serials() -> list[tuple[int, str]]:
    """Read machine number and serial from Tik1.xlsx."""
    if not os.path.exists(TIK1_WORKBOOK):
        return []
    import openpyxl
    wb = openpyxl.load_workbook(TIK1_WORKBOOK, data_only=True)
    ws = wb.active
    res = []
    for r in range(2, ws.max_row + 1):
        m_val = ws.cell(r, 1).value
        s_val = ws.cell(r, 2).value
        if m_val is not None and s_val is not None:
            try:
                m_num = int(m_val)
                serial = str(s_val).strip()
                if serial:
                    res.append((m_num, serial))
            except ValueError:
                continue
    return res


def clear_device_cache(m_num: int, serial: str) -> tuple[int, str, bool, str]:
    """Process a single device: acquire DeviceLock -> clear cache -> force stop -> home."""
    if DeviceLock is None:
        return m_num, serial, False, f"[ERROR] DeviceLock not available for machine {m_num}"

    try:
        lock = DeviceLock(
            serial=serial,
            machine=str(m_num),
            project="clear-cache",
            bypass_proxy_readiness=True,
            user_authorized=False,
        )
    except (DeviceLockUnavailable, DeviceLockNeedsUserDecision):
        return m_num, serial, False, f"[LOCKED] Machine {m_num} is busy"
    except Exception as exc:
        return m_num, serial, False, f"[ERROR] Machine {m_num} lock init failed: {exc}"

    cmd = [
        sys.executable,
        SCRIPT_PATH,
        "--machine", str(m_num),
        "--serial", serial,
        "--widget-pos", f"{DEFAULT_WIDGET_POS[0]},{DEFAULT_WIDGET_POS[1]}",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = r"D:\Taadaa\automation-core\src;D:\Taadaa\tiktok-luot nuoi acc"

    msg = ""
    ok = False

    try:
        with lock:
            try:
                p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=240, **WIN_KWARGS)
                out = p.stdout.strip() or p.stderr.strip()
                if p.returncode == 0:
                    msg = f"[OK] Machine {m_num}: {out}"
                    ok = True
                else:
                    msg = f"[WARN] Machine {m_num} (code {p.returncode}): {out}"
            except subprocess.TimeoutExpired:
                msg = f"[TIMEOUT] Machine {m_num} [{serial}] cache clear timed out after 240s"
            except Exception as exc:
                msg = f"[ERROR] Machine {m_num} [{serial}] error: {exc}"
            finally:
                # Guarantee: Force stop TikTok, press Home, and ensure portrait lock
                try:
                    subprocess.run(
                        [
                            ADB, "-s", serial, "shell",
                            "am force-stop com.ss.android.ugc.trill; "
                            "input keyevent KEYCODE_HOME; "
                            "settings put system accelerometer_rotation 0; "
                            "settings put system user_rotation 0"
                        ],
                        capture_output=True,
                        timeout=10,
                        **WIN_KWARGS,
                    )
                except Exception:
                    pass
    except (DeviceLockUnavailable, DeviceLockNeedsUserDecision):
        return m_num, serial, False, f"[LOCKED] Machine {m_num} is busy"
    except Exception as exc:
        return m_num, serial, False, f"[ERROR] Machine {m_num} lock acquisition failed: {exc}"

    return m_num, serial, ok, msg


def _send_clear_cache_alert(error_reason: str) -> None:
    try:
        from automation_core.alerts import send_farm_script_alert
        send_farm_script_alert(
            script_name="clear_cache",
            error_reason=error_reason,
            flow_file=str(Path(__file__).resolve()),
            log_path=r"D:/Taadaa/runtime/kibe/reports",
            canary_cmd="python C:/Users/Kibe/AppData/Local/hermes/scripts/cron_clear_tiktok_cache.py",
        )
    except Exception as exc:
        sys.stderr.write(f"[ALERT FAILED] {exc}\n")


def is_ca4_finished(today_str: str) -> bool:
    if not REPORTED_FILE.is_file():
        return False
    try:
        data = json.loads(REPORTED_FILE.read_text(encoding="utf-8"))
        sessions = set(data.get("reported_sessions", []))
        return f"{today_str}_ca4_phien2" in sessions or f"{today_str}_ca4" in sessions
    except Exception:
        return False


def load_state(today_str: str) -> dict:
    if not STATE_FILE.is_file():
        return {"last_date": today_str, "cleared_machines": [], "machine_retries": {}, "reported_date": None}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if data.get("last_date") != today_str:
            return {"last_date": today_str, "cleared_machines": [], "machine_retries": {}, "reported_date": None}
        if "machine_retries" not in data:
            data["machine_retries"] = {}
        return data
    except Exception as exc:
        sys.stderr.write(f"[WARN] Failed to read state file: {exc}\n")
        return {"last_date": today_str, "cleared_machines": [], "machine_retries": {}, "reported_date": None}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["last_run_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        sys.stderr.write(f"[WARN] Failed to save state file: {exc}\n")


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Clear TikTok Cache Watchdog sau Ca 4")
    parser.add_argument("--force", action="store_true", help="Bypass time window and session checks")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args, _ = parser.parse_known_args()

    today_str = datetime.now().strftime("%Y-%m-%d")
    now_hour = datetime.now().hour

    if not args.force:
        if not (3 <= now_hour <= 5):
            return 0
        if is_feed_runner_active():
            return 0
        if not is_ca4_finished(today_str):
            return 0

    state_data = load_state(today_str)
    cleared_today = set(state_data.get("cleared_machines", []))
    machine_retries = state_data.get("machine_retries", {})

    connected = get_connected_devices()
    if not connected:
        return 0

    machines = load_machine_serials()
    if not machines:
        return 0

    target_machines = [
        (m, s) for m, s in machines
        if s in connected and m not in cleared_today and machine_retries.get(str(m), 0) < 2
    ]
    if not target_machines:
        # All connected machines have been cleared today or reached retry limit
        return 0

    if args.dry_run:
        sys.stderr.write(f"[CRON][DRY-RUN] Would clear {len(target_machines)} machines; state unchanged.\n")
        return 0

    sys.stderr.write(f"[CRON] Starting concurrent TikTok cache clear on {len(target_machines)} machines (workers={MAX_WORKERS})...\n")

    success_machines: list[int] = []
    failed_machines: list[tuple[int, str]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(clear_device_cache, m, s): m for m, s in target_machines}
        for future in concurrent.futures.as_completed(futures):
            m_num, serial, ok, msg = future.result()
            sys.stderr.write(f"{msg}\n")
            if ok:
                success_machines.append(m_num)
                cleared_today.add(m_num)
                state_data["cleared_machines"] = sorted(list(cleared_today))
                save_state(state_data)
            else:
                if "[LOCKED]" in msg:
                    # Ignore locked machines to avoid spamming reports
                    continue

                machine_retries[str(m_num)] = machine_retries.get(str(m_num), 0) + 1
                state_data["machine_retries"] = machine_retries
                save_state(state_data)

                reason = "Error"
                if "WIDGET_MISS" in msg:
                    reason = "WIDGET_MISS"
                elif "timed out" in msg.lower() or "timeout" in msg.lower():
                    reason = "Timeout"
                elif "[WARN]" in msg or "[ERROR]" in msg:
                    parts = msg.split(":", 2)
                    reason = parts[2].strip() if len(parts) >= 3 else parts[-1].strip()
                failed_machines.append((m_num, reason))

    s_count = len(success_machines)
    f_count = len(failed_machines)
    total_attempted = len(target_machines)

    # Anti-spam alert:
    # 1. Chỉ cảnh báo nếu tỷ lệ fail thực sự lớn trên quy mô farm (ít nhất 5 máy fail và > 30% số máy quét)
    # 2. Debounce: Chỉ báo duy nhất 1 lần trong ngày đối với cùng danh sách/nội dung lỗi (alert-once)
    if total_attempted > 0 and f_count >= 5 and f_count > (total_attempted * 0.3):
        f_summary_str = ", ".join(f"{m:02d} ({r})" for m, r in sorted(failed_machines))
        alert_msg = f"Đa số máy dọn cache thất bại/timeout ({f_count}/{total_attempted} máy fail): {f_summary_str}"
        if state_data.get("last_alert_date") != today_str or state_data.get("last_alert_msg") != alert_msg:
            _send_clear_cache_alert(alert_msg)
            state_data["last_alert_date"] = today_str
            state_data["last_alert_msg"] = alert_msg
            save_state(state_data)

    if s_count == 0:
        sys.stderr.write(f"[CRON] s_count == 0 ({f_count} failed), im lặng không xuất stdout.\n")
        return 0

    s_list = ", ".join(f"{m:02d}" for m in sorted(success_machines))

    if state_data.get("reported_date") == today_str:
        if len(cleared_today) >= len(connected):
            print(f"[DỌN CACHE TIKTOK] Đã dọn bù thành công: {s_list}. Toàn farm hoàn tất {len(cleared_today)}/{len(connected)} máy.")
        else:
            sys.stderr.write(f"[CRON] Đã dọn bù {s_count} máy ({s_list}). Đã báo cáo hôm nay rồi, im lặng.\n")
        return 0

    # Đợt báo cáo đầu tiên trong ngày (reported_date != today_str)
    report = [
        f"[BÁO CÁO DỌN DẸP CACHE TIKTOK]",
        f"• Đã dọn đợt này: {s_count} máy ({s_list})",
        f"• Lũy kế hôm nay: {len(cleared_today)} máy",
    ]

    if f_count > 0:
        f_list = ", ".join(f"{m:02d}" for m, _ in sorted(failed_machines))
        report.append(f"• Fail ({f_count}): {f_list}")
        for m, reason in sorted(failed_machines):
            report.append(f"  - Máy {m:02d}: {reason}")
    else:
        report.append(f"• Fail (0)")

    print("\n".join(report))
    state_data["reported_date"] = today_str
    save_state(state_data)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        _send_clear_cache_alert(f"Lỗi script nghiêm trọng: {exc}")
        raise

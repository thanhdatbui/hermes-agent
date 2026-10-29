#!/usr/bin/env python3
"""
farm_idle_screen_and_app_healer.py
Watchdog tự động chuẩn hóa trạng thái idle cho Dual-Cluster Farm (Kibe Local + Admin Remote):
1. Bỏ qua các máy đang có lock file hoạt động (active PID).
2. Với máy nhàn rỗi:
   - Đảm bảo screen_off_timeout = 600000 (10 phút).
   - Đảm bảo stay_on_while_plugged_in = 0 và svc power stayon false.
   - Nếu phát hiện app TikTok đang chiếm focus trên máy idle -> am force-stop và input keyevent 3 về HOME.
3. Chạy song song max_workers=30 với timeout mỗi lệnh <= 3s, chống nghẽn tuyệt đối.
"""

import os
import re
import sys
import json
import time
import uuid
import logging
import shutil
import ctypes
import subprocess
import socket
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ADB_BIN = r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe"
if not os.path.exists(ADB_BIN):
    ADB_BIN = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
if not os.path.exists(ADB_BIN):
    ADB_BIN = "adb"

ADMIN_IP = "192.168.110.119"
ADMIN_PORT = 5037

KIBE_EXCEL = r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx"
ADMIN_EXCEL = r"D:\OneDrive\TaadaaData\admin\PROXYgandienthoai.xlsx"
LOCKS_DIR = Path.home() / ".codex" / "device-locks"

logger = logging.getLogger("farm_idle_healer")


def is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if h:
            kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        return False


def load_mapping(excel_path: str) -> dict[str, int]:
    mapping = {}
    if not os.path.exists(excel_path):
        logger.warning("load_mapping: file Excel không tồn tại: %s", excel_path)
        return mapping
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_path, data_only=True)
        sheet = wb.active
        for r in range(2, sheet.max_row + 1):
            m = sheet.cell(row=r, column=1).value
            s = sheet.cell(row=r, column=2).value
            if m is not None and s:
                try:
                    mapping[str(s).strip()] = int(m)
                except ValueError:
                    logger.warning("load_mapping: dòng %d (%s) có số máy không hợp lệ: %r", r, excel_path, m)
    except Exception as exc:
        logger.warning("load_mapping: lỗi đọc Excel %s: %s: %s", excel_path, type(exc).__name__, exc)
    return mapping


def get_locked_devices(mapping=None) -> tuple[set[int], set[str]]:
    """Return locked machine IDs and serials, failing closed for recent or unreadable locks."""
    locked_machines = set()
    locked_serials = set()
    if LOCKS_DIR.exists():
        active_statuses = {
            "running", "queued", "queued_v2", "recovery", "blocked",
            "failed_locked", "handoff", "user_pinned",
        }
        current_host = socket.gethostname()

        for lf in LOCKS_DIR.glob("*.lock.json"):
            machine_match = re.search(r"machine_(\d+)", lf.name)
            serial_match = re.search(r"(?:serial_|machine_\d+\.)([^.]+)", lf.name)
            filename_machine = int(machine_match.group(1)) if machine_match else None
            filename_serial = serial_match.group(1) if serial_match else None

            try:
                with open(lf, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("lock JSON must contain an object")

                machine_value = data.get("machine") or data.get("stt") or filename_machine
                serial_value = data.get("serial") or data.get("device_id") or filename_serial
                try:
                    machine = int(machine_value) if machine_value is not None else None
                except (TypeError, ValueError):
                    machine = filename_machine
                serial = str(serial_value).strip() if serial_value is not None else None
                if serial == "":
                    serial = None

                pid = data.get("pid") or data.get("holder_pid") or 0
                try:
                    pid_alive = bool(pid) and is_pid_alive(int(pid))
                except (TypeError, ValueError, OverflowError):
                    pid_alive = False

                host = data.get("host")
                status = str(data.get("status") or "").strip().lower()
                try:
                    recent = time.time() - lf.stat().st_mtime < 3600
                except OSError:
                    recent = True

                is_locked = (
                    pid_alive
                    or (host is not None and str(host) != current_host)
                    or status in active_statuses
                    or recent
                )
                if is_locked:
                    if machine is not None:
                        locked_machines.add(machine)
                    if serial:
                        locked_serials.add(serial)
                else:
                    logger.debug(
                        "get_locked_devices: bỏ qua stale lock %s (pid=%s, status=%s)",
                        lf.name, pid, status,
                    )
            except Exception as exc:
                # A malformed lock is still a lock: recover whatever identity
                # can be established from its filename.
                logger.warning(
                    "get_locked_devices: không đọc được lock %s: %s: %s",
                    lf.name, type(exc).__name__, exc,
                )
                if filename_machine is not None:
                    locked_machines.add(filename_machine)
                if filename_serial:
                    locked_serials.add(filename_serial)

    if mapping:
        for serial, machine_value in mapping.items():
            try:
                machine = int(machine_value)
            except (TypeError, ValueError):
                continue
            serial = str(serial).strip()
            if machine in locked_machines:
                locked_serials.add(serial)
            if serial in locked_serials:
                locked_machines.add(machine)

    return locked_machines, locked_serials


def get_online_devices(base_cmd: list[str]) -> list[str]:
    try:
        res = subprocess.run(base_cmd + ["devices"], capture_output=True, text=True, timeout=5)
        lines = res.stdout.strip().split("\n")[1:]
        devices = []
        for l in lines:
            parts = l.strip().split("\t")
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception as exc:
        logger.warning("get_online_devices: lỗi `%s devices`: %s: %s", " ".join(base_cmd), type(exc).__name__, exc)
        return []


def heal_device(cluster_base_cmd: list[str], serial: str, m_num: int, is_locked: bool, correlation_id: str = "") -> dict:
    cid = correlation_id or uuid.uuid4().hex[:8]
    if is_locked:
        logger.info("[%s] M%s %s: locked, bỏ qua", cid, m_num, serial)
        return {"machine": m_num, "serial": serial, "status": "locked", "actions": [], "errors": [], "correlation_id": cid, "duration_ms": 0.0}

    cmd_prefix = cluster_base_cmd + ["-s", serial, "shell"]
    t0 = time.time()
    actions, errors = [], []

    # 1. Screen power and timeout check
    try:
        res_to = subprocess.run(cmd_prefix + ["settings", "get", "system", "screen_off_timeout"], capture_output=True, text=True, timeout=3)
        timeout_val = (res_to.stdout or "").strip()
        res_so = subprocess.run(cmd_prefix + ["settings", "get", "global", "stay_on_while_plugged_in"], capture_output=True, text=True, timeout=3)
        stayon_val = (res_so.stdout or "").strip()

        if timeout_val != "600000" or stayon_val != "0":
            subprocess.run(cmd_prefix + ["settings", "put", "system", "screen_off_timeout", "600000"], capture_output=True, text=True, timeout=3)
            subprocess.run(cmd_prefix + ["settings", "put", "global", "stay_on_while_plugged_in", "0"], capture_output=True, text=True, timeout=3)
            subprocess.run(cmd_prefix + ["svc", "power", "stayon", "false"], capture_output=True, text=True, timeout=3)
            actions.append(f"timeout_healed ({timeout_val}->600000)")
    except Exception as exc:
        errors.append(f"timeout_check: {exc}")
        logger.warning("[%s] M%s %s: timeout_check lỗi: %s: %s", cid, m_num, serial, type(exc).__name__, exc)

    # 2. Dập tắt TikTok còn sót trên máy nhàn rỗi
    try:
        res_pid = subprocess.run(cmd_prefix + ["pidof", "com.ss.android.ugc.trill", "com.zhiliaoapp.musically"], capture_output=True, text=True, timeout=3)
        if (res_pid.stdout or "").strip():
            subprocess.run(cmd_prefix + ["am", "force-stop", "com.ss.android.ugc.trill"], capture_output=True, text=True, timeout=3)
            subprocess.run(cmd_prefix + ["am", "force-stop", "com.zhiliaoapp.musically"], capture_output=True, text=True, timeout=3)
            subprocess.run(cmd_prefix + ["input", "keyevent", "3"], capture_output=True, text=True, timeout=3)
            actions.append("tiktok_stopped_to_home")
    except Exception as exc:
        errors.append(f"tiktok_check: {exc}")
        logger.warning("[%s] M%s %s: tiktok_check lỗi: %s: %s", cid, m_num, serial, type(exc).__name__, exc)

    # 3. Tắt màn hình về sleep (keyevent 223) nếu màn hình đang sáng trên máy nhàn rỗi
    try:
        res_pwr = subprocess.run(cmd_prefix + ["dumpsys", "power"], capture_output=True, text=True, timeout=3)
        pwr_text = res_pwr.stdout or ""
        if "mWakefulness=Awake" in pwr_text or "Display Power: state=ON" in pwr_text:
            subprocess.run(cmd_prefix + ["input", "keyevent", "223"], capture_output=True, text=True, timeout=3)
            actions.append("screen_turned_off")
    except Exception as exc:
        errors.append(f"power_check: {exc}")
        logger.warning("[%s] M%s %s: power_check lỗi: %s: %s", cid, m_num, serial, type(exc).__name__, exc)

    dur = round((time.time() - t0) * 1000.0, 1)
    status = "healed" if actions else ("error" if errors else "clean")
    logger.info("[%s] M%s %s: %s actions=%s errors=%d duration_ms=%s", cid, m_num, serial, status, actions, len(errors), dur)
    return {
        "machine": m_num,
        "serial": serial,
        "status": status,
        "actions": actions,
        "errors": errors,
        "duration_ms": dur,
        "correlation_id": cid,
    }


def is_near_reboot_window(buffer_minutes: int = 10) -> bool:
    """Kiểm tra thời điểm hiện tại có cận kề các mốc Auto-Reboot Farm (05:20, 11:20, 17:20) không."""
    now = time.localtime()
    cur_m = now.tm_hour * 60 + now.tm_min
    reboot_minutes = [5 * 60 + 20, 11 * 60 + 20, 17 * 60 + 20]
    for rm in reboot_minutes:
        if abs(cur_m - rm) <= buffer_minutes:
            return True
    return False


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_id = uuid.uuid4().hex[:8]
    run_t0 = time.time()
    if is_near_reboot_window():
        logger.info("[%s] skip: cận kề cửa sổ Auto-Reboot", run_id)
        print("[SKIP] Cận kề cửa sổ Auto-Reboot Farm (05:20 / 11:20 / 17:20), tạm dừng healer để tránh timeout ADB.")
        return 0

    mapping = {**load_mapping(KIBE_EXCEL), **load_mapping(ADMIN_EXCEL)}
    if not mapping:
        logger.warning("[%s] mapping serial->máy rỗng: toàn bộ thiết bị sẽ không xác định được số máy/lock theo máy", run_id)
    locked_machines, locked_serials = get_locked_devices(mapping)

    clusters = [
        {"name": "Kibe Local", "base_cmd": [ADB_BIN]},
        {"name": "Admin Remote", "base_cmd": [ADB_BIN, "-H", ADMIN_IP, "-P", str(ADMIN_PORT)]},
    ]

    total_online = 0
    total_locked = 0
    healed_timeout = []
    stopped_tiktok = []
    turned_off_screen = []
    failed_devices = []
    status_counts = {}

    tasks = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        for cluster in clusters:
            base_cmd = cluster["base_cmd"]
            devices = get_online_devices(base_cmd)
            total_online += len(devices)
            for s in devices:
                m_num = mapping.get(s, 0)
                is_locked = (m_num in locked_machines) or (s in locked_serials)
                if is_locked:
                    total_locked += 1
                future = executor.submit(heal_device, base_cmd, s, m_num, is_locked, f"{run_id}-{s[-6:]}")
                tasks.append(future)

        for future in as_completed(tasks):
            try:
                res = future.result()
                actions = res.get("actions", [])
                status_counts[res.get("status", "unknown")] = status_counts.get(res.get("status", "unknown"), 0) + 1
                if res.get("errors"):
                    failed_devices.append(res["serial"])
                m_label = f"M{res['machine']:02d}" if res['machine'] else res['serial'][:8]
                for act in actions:
                    if "timeout_healed" in act:
                        healed_timeout.append(f"{m_label} ({act})")
                    if "tiktok_stopped_to_home" in act:
                        stopped_tiktok.append(m_label)
                    if "screen_turned_off" in act:
                        turned_off_screen.append(m_label)
            except Exception as exc:
                logger.error("[%s] heal_device future lỗi: %s: %s", run_id, type(exc).__name__, exc)
                status_counts["crashed"] = status_counts.get("crashed", 0) + 1

    print(f"=== BÁO CÁO DỌN DẸP FARM CHUẨN HÓA MÀN HÌNH & APP ===")
    print(f"• Tổng thiết bị online: {total_online}")
    print(f"• Thiết bị đang bận (locked, bỏ qua): {total_locked}")
    print(f"• Thiết bị khôi phục timeout 10 phút ({len(healed_timeout)} máy): {', '.join(sorted(healed_timeout)) if healed_timeout else 'Tất cả đã chuẩn'}")
    print(f"• Thiết bị force-stop TikTok về HOME ({len(stopped_tiktok)} máy): {', '.join(sorted(stopped_tiktok)) if stopped_tiktok else 'Không có app treo'}")
    print(f"• Thiết bị tắt màn hình ({len(turned_off_screen)} máy): {', '.join(sorted(turned_off_screen)) if turned_off_screen else 'Màn hình đã ngủ sẵn'}")
    telemetry = {
        "event": "idle_healer_done",
        "run_id": run_id,
        "online": total_online,
        "locked": total_locked,
        "healed": len(healed_timeout),
        "stopped": len(stopped_tiktok),
        "off": len(turned_off_screen),
        "errors": len(failed_devices),
        "failed_serials": sorted(failed_devices),
        "status_counts": status_counts,
        "duration_ms": round((time.time() - run_t0) * 1000.0, 1),
    }
    print(f"[TELEMETRY_METRIC] {json.dumps(telemetry)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

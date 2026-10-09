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
import shutil
import ctypes
import subprocess
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
                    pass
    except Exception:
        pass
    return mapping


def get_locked_devices() -> tuple[set[int], set[str]]:
    locked_machines = set()
    locked_serials = set()
    if not LOCKS_DIR.exists():
        return locked_machines, locked_serials

    for lf in LOCKS_DIR.glob("*.lock.json"):
        try:
            with open(lf, "r", encoding="utf-8") as f:
                data = json.load(f)
            pid = data.get("pid") or data.get("holder_pid") or 0
            if pid and is_pid_alive(int(pid)):
                if lf.name.startswith("machine_"):
                    m_str = lf.name.replace("machine_", "").replace(".lock.json", "")
                    if m_str.isdigit():
                        locked_machines.add(int(m_str))
                elif lf.name.startswith("serial_"):
                    s_str = lf.name.replace("serial_", "").replace(".lock.json", "")
                    locked_serials.add(s_str)
            else:
                pass
        except Exception:
            pass
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
    except Exception:
        return []


def heal_device(cluster_base_cmd: list[str], serial: str, m_num: int, is_locked: bool) -> dict:
    if is_locked:
        return {"machine": m_num, "serial": serial, "status": "locked", "actions": []}

    cmd_prefix = cluster_base_cmd + ["-s", serial, "shell"]
    actions = []

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
    except Exception:
        pass

    # 2. Check focus for lingering TikTok
    try:
        res_win = subprocess.run(cmd_prefix + ["dumpsys", "window"], capture_output=True, text=True, timeout=4)
        out = res_win.stdout or ""
        focus_lines = [l for l in out.splitlines() if "mCurrentFocus" in l or "mFocusedApp" in l]
        focus_text = " ".join(focus_lines)
        if "com.ss.android.ugc.trill" in focus_text or "com.zhiliaoapp.musically" in focus_text:
            subprocess.run(cmd_prefix + ["am", "force-stop", "com.ss.android.ugc.trill"], capture_output=True, text=True, timeout=3)
            subprocess.run(cmd_prefix + ["input", "keyevent", "3"], capture_output=True, text=True, timeout=3)
            actions.append("tiktok_stopped_to_home")
    except Exception:
        pass

    return {
        "machine": m_num,
        "serial": serial,
        "status": "healed" if actions else "clean",
        "actions": actions,
    }


def main():
    mapping = {**load_mapping(KIBE_EXCEL), **load_mapping(ADMIN_EXCEL)}
    locked_machines, locked_serials = get_locked_devices()

    clusters = [
        {"name": "Kibe Local", "base_cmd": [ADB_BIN]},
        {"name": "Admin Remote", "base_cmd": [ADB_BIN, "-H", ADMIN_IP, "-P", str(ADMIN_PORT)]},
    ]

    total_online = 0
    total_locked = 0
    healed_timeout = []
    stopped_tiktok = []

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
                future = executor.submit(heal_device, base_cmd, s, m_num, is_locked)
                tasks.append(future)

        for future in as_completed(tasks):
            try:
                res = future.result()
                actions = res.get("actions", [])
                m_label = f"M{res['machine']:02d}" if res['machine'] else res['serial'][:8]
                for act in actions:
                    if "timeout_healed" in act:
                        healed_timeout.append(f"{m_label} ({act})")
                    if "tiktok_stopped_to_home" in act:
                        stopped_tiktok.append(m_label)
            except Exception:
                pass

    if healed_timeout or stopped_tiktok:
        print(f"=== BÁO CÁO DỌN DẸP FARM CHUẨN HÓA MÀN HÌNH & APP ===")
        print(f"• Tổng thiết bị online: {total_online}")
        print(f"• Thiết bị đang bận (locked, bỏ qua): {total_locked}")
        print(f"• Thiết bị khôi phục timeout 10 phút ({len(healed_timeout)} máy): {', '.join(sorted(healed_timeout)) if healed_timeout else 'Tất cả đã chuẩn'}")
        print(f"• Thiết bị force-stop TikTok về HOME ({len(stopped_tiktok)} máy): {', '.join(sorted(stopped_tiktok)) if stopped_tiktok else 'Không có app treo'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

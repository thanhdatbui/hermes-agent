#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_morning_gmail_2fa_watchdog.py
Watchdog cuốn chiếu: Bật 2FA Gmail sau khi Ca 1 nuôi feed hoàn thành.
Khung giờ: 08:30 - 11:30 (HCM).
"""

import os
import sys
import json
import glob
import time
import shutil
import argparse
import subprocess
from datetime import datetime

# Định nghĩa đường dẫn
STATE_DIR = r"D:\Taadaa\runtime\kibe\cron-state"
STATE_FILE = os.path.join(STATE_DIR, "post_morning_gmail_2fa_state.json")
FEED_REPORTED_FILE = os.path.join(STATE_DIR, "feed_session_reported.json")
LOCK_DIR = r"D:\Taadaa\runtime\device_locks"
EXCEL_CANDIDATE_PATHS = [
    r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx",
    r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx",
    r"D:\Taadaa\tiktok-add-2fa\gmail_clean_v2.xlsx",
    r"D:\Taadaa\gmail_clean_v2.xlsx",
    r"D:\Taadaa\tools\gmail_clean_v2.xlsx",
]
ENABLE_SCRIPT_PATHS = [
    r"D:\Taadaa\tiktok-add-2fa\enable_gmail_2fa_device.py",
    r"D:\Taadaa\tools\enable_gmail_2fa_device.py",
    r"C:\Users\Kibe\AppData\Local\hermes\scripts\enable_gmail_2fa_device.py",
]


def log(msg: str):
    # Ghi ra stderr để debug nếu cần, không in ra stdout để tránh trigger Telegram delivery
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys.stderr.write(f"[{now_str}] {msg}\n")


def is_within_time_window(start_hm=(8, 30), end_hm=(11, 30)) -> bool:
    now = datetime.now()
    cur_hm = (now.hour, now.minute)
    return start_hm <= cur_hm <= end_hm


def is_already_run_today() -> bool:
    if not os.path.isfile(STATE_FILE):
        return False
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get("last_success_date") == today
    except Exception as e:
        log(f"Lỗi đọc state file: {e}")
        return False


def save_state_success(details: dict = None):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        data = {
            "last_success_date": today,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "details": details or {}
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log(f"Đã cập nhật state file: {STATE_FILE}")
    except Exception as e:
        log(f"Lỗi ghi state file: {e}")


def is_feed_ca1_finished() -> bool:
    if not os.path.isfile(FEED_REPORTED_FILE):
        log(f"Không tìm thấy file {FEED_REPORTED_FILE}")
        return False
    try:
        with open(FEED_REPORTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        keys = [f"{today}_ca1_phien2", f"{today}_ca1", f"{today}_ca1_phien3"]
        if isinstance(data, dict):
            reported = set(data.get("reported_sessions", []))
            if any(k in reported for k in keys):
                return True
            for k in keys:
                if k in data and data[k]:
                    return True
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, str) and any(k in item for k in keys):
                    return True
                if isinstance(item, dict):
                    sid = item.get("session_id") or item.get("id") or ""
                    if any(k in sid for k in keys):
                        return True
        return False
    except Exception as e:
        log(f"Lỗi kiểm tra feed session reported: {e}")
        return False


def is_feed_runner_active() -> bool:
    try:
        cmd = 'tasklist /FI "IMAGENAME eq python.exe" /FO CSV /NH'
        out = subprocess.check_output(cmd, shell=True, text=True, errors="ignore")
        # Kiểm tra chi tiết qua wmic/powershell nếu cần, hoặc kiểm tra commandline
        ps_cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Select-Object -ExpandProperty CommandLine"'
        ps_out = subprocess.check_output(ps_cmd, shell=True, text=True, errors="ignore")
        keywords = ["feed_session_runner", "run_feed_session", "feed_consumer"]
        for line in ps_out.splitlines():
            if any(kw in line.lower() for kw in keywords):
                return True
        return False
    except Exception as e:
        # Fallback an toàn
        return False


def has_active_device_locks() -> bool:
    lock_dirs = [
        os.path.expanduser(r"~/.codex/device-locks"),
        os.path.expanduser(r"~\AppData\Local\automation-core\device-locks"),
    ]
    for ld in lock_dirs:
        if os.path.isdir(ld):
            try:
                for f in glob.glob(os.path.join(ld, "*.lock.json")):
                    try:
                        with open(f, "r", encoding="utf-8") as fp:
                            data = json.load(fp)
                            st = data.get("status")
                            if st in ("active", "running", "queued", "queued_v2"):
                                return True
                            if st == "blocked" and data.get("owner_active", True) is not False:
                                return True
                    except Exception:
                        pass
                for f in glob.glob(os.path.join(ld, "*.lock")):
                    return True
            except Exception:
                pass
    return False


def get_online_devices() -> list:
    try:
        out = subprocess.check_output("adb devices", shell=True, text=True, errors="ignore")
        devices = []
        for line in out.strip().splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    except Exception as e:
        log(f"Lỗi lấy adb devices: {e}")
        return []


def find_existing_file(path_list: list) -> str:
    for p in path_list:
        if os.path.isfile(p):
            return p
    return ""


def scan_candidates(excel_path: str) -> list:
    if not excel_path or not os.path.isfile(excel_path):
        log(f"Không tìm thấy file Excel candidate tại các đường dẫn quy định.")
        return []
    try:
        import pandas as pd
        df = pd.read_excel(excel_path)
        candidates = []
        # Tìm cột tương ứng: days_ago / created_at / 2fa status
        # Tiêu chí: days_ago >= 1 (ngâm 24-48h) và chưa có 2FA
        col_2fa = None
        for c in df.columns:
            if "2fa" in str(c).lower():
                col_2fa = c
                break
        
        col_days = None
        for c in df.columns:
            if "days" in str(c).lower() or "ngam" in str(c).lower() or "age" in str(c).lower():
                col_days = c
                break

        col_device = None
        for c in df.columns:
            if "device" in str(c).lower() or "serial" in str(c).lower() or "may" in str(c).lower():
                col_device = c
                break

        for idx, row in df.iterrows():
            has_2fa = False
            if col_2fa:
                val = str(row[col_2fa]).strip().lower()
                if val in ["yes", "true", "1", "done", "x", "ok"]:
                    has_2fa = True

            days = 1
            if col_days:
                try:
                    days = float(row[col_days])
                except Exception:
                    days = 1

            dev = str(row[col_device]).strip() if col_device else ""
            if not has_2fa and days >= 1:
                candidates.append({
                    "index": idx,
                    "device": dev,
                    "email": row.get("email") or row.get("Email") or f"row_{idx}",
                    "row": row.to_dict()
                })
        return candidates
    except Exception as e:
        log(f"Lỗi đọc candidate từ Excel: {e}")
        return []


def run_enable_2fa(device_id: str, enable_script: str, dry_run: bool = False) -> bool:
    if dry_run:
        time.sleep(0.5)
        return True
    try:
        cmd = [sys.executable, enable_script, "--device", device_id]
        log(f"Đang chạy lệnh: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return res.returncode == 0
    except Exception as e:
        log(f"Lỗi khi bật 2FA cho device {device_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Watchdog bật 2FA Gmail sau Ca 1.")
    parser.add_argument("--dry-run", action="store_true", help="Chạy giả lập, không tác động thiết bị")
    parser.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra giờ và trạng thái feed/lock")
    args = parser.parse_args()

    # 1. Kiểm tra idempotency
    if not args.force and is_already_run_today():
        return 0

    # 2. Kiểm tra khung giờ
    if not args.force and not is_within_time_window((8, 30), (11, 30)):
        return 0

    # 3. Kiểm tra ca 1 hoàn thành
    if not args.force and not is_feed_ca1_finished():
        return 0

    # 4. Kiểm tra Idle
    if not args.force:
        if is_feed_runner_active():
            return 0
        if has_active_device_locks():
            return 0

    log("Đủ điều kiện kích hoạt bật 2FA Gmail sau Ca 1!")

    excel_path = find_existing_file(EXCEL_CANDIDATE_PATHS)
    enable_script = find_existing_file(ENABLE_SCRIPT_PATHS)

    start_time = datetime.now()
    online_devices = get_online_devices()
    log(f"Online devices hiện tại: {online_devices}")

    candidates = scan_candidates(excel_path)
    log(f"Tìm thấy {len(candidates)} account/dòng thỏa mãn ngâm >= 1 ngày và chưa có 2FA.")

    # Gom danh sách thiết bị cần chạy
    eligible_devices = []
    if online_devices:
        eligible_devices = online_devices
    else:
        if args.dry_run:
            eligible_devices = ["DEVICE_DRYRUN_01", "DEVICE_DRYRUN_02"]
        else:
            log("Không có thiết bị online để thao tác.")

    success_list = []
    fail_list = []

    for dev in eligible_devices:
        log(f"-> Xử lý bật 2FA trên thiết bị: {dev}")
        ok = run_enable_2fa(dev, enable_script, dry_run=args.dry_run)
        if ok:
            success_list.append(dev)
        else:
            fail_list.append(dev)

    end_time = datetime.now()
    duration_min = round((end_time - start_time).total_seconds() / 60, 1)

    report = f"""
[BÁO CÁO 2FA GMAIL SAU CA SÁNG]
- Thời gian: {start_time.strftime('%H:%M')} -> {end_time.strftime('%H:%M')} ({duration_min} phút)
- Tổng máy đủ điều kiện: {len(eligible_devices)}
- Success (S): {success_list}
- Fail (F): {fail_list}
"""
    print(report)

    if not args.dry_run and len(success_list) > 0:
        save_state_success({
            "success_devices": success_list,
            "fail_devices": fail_list,
            "duration_min": duration_min
        })

    return 0


if __name__ == "__main__":
    sys.exit(main())

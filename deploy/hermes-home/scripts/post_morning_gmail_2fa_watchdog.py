#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_morning_gmail_2fa_watchdog.py
Watchdog cuốn chiếu: Bật 2FA Gmail sau khi Ca 1 nuôi feed hoàn thành.
Khung giờ: 08:30 - 11:30 (HCM).
Silent Watchdog: Tuyệt đối không in ra stdout nếu không có kết quả hành động.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path

# Định nghĩa đường dẫn
ADB_EXE = r"C:\Users\Kibe\.GemPhoneFarm\app\adb-tool\adb.exe"
STATE_DIR = r"D:\Taadaa\runtime\kibe\cron-state"
STATE_FILE = os.path.join(STATE_DIR, "post_morning_gmail_2fa_state.json")
FEED_REPORTED_FILE = os.path.join(STATE_DIR, "feed_session_reported.json")
CLEAN_XLSX = Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx")
PROXY_XLSX = Path(r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx")
LOCK_DIR = Path(r"C:\Users\Kibe\AppData\Local\automation-core\device-locks")

# Import module cron nuôi acc để đọc lịch chạy
sys.path.insert(0, r"D:\Taadaa\tiktok-luot nuoi acc")
try:
    from python_runner.hermes_cron.models import StatePaths, parse_hcm_timestamp
    from python_runner.hermes_cron.manifest import load_active
    from python_runner.hermes_cron.source_config import SourceConfig
    CRON_MODULE_AVAILABLE = True
except Exception:
    CRON_MODULE_AVAILABLE = False

sys.path.insert(0, r"D:\Taadaa\tools")
try:
    from enable_gmail_2fa_device import enable_2fa_device
except ImportError:
    enable_2fa_device = None


def log(msg: str):
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
        ps_cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \\"Name=\'python.exe\'\\" | Select-Object -ExpandProperty CommandLine"'
        ps_out = subprocess.check_output(ps_cmd, shell=True, text=True, errors="ignore")
        keywords = ["feed_session_runner", "run_feed_session", "feed_consumer", "multi_machine_feed_session"]
        for line in ps_out.splitlines():
            if any(kw in line.lower() for kw in keywords):
                return True
        return False
    except Exception:
        return False


def get_online_devices() -> set:
    try:
        res = subprocess.run([ADB_EXE, "devices"], capture_output=True, text=True, timeout=10)
        online = set()
        for line in res.stdout.splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                online.add(parts[0])
        return online
    except Exception as e:
        log(f"Lỗi lấy adb devices: {e}")
        return set()


def get_active_locks() -> set:
    active = set()
    if LOCK_DIR.exists():
        for f in LOCK_DIR.glob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                if d.get("status") in ["active", "running", "queued", "blocked"]:
                    m = d.get("machine")
                    if m is not None:
                        active.add(int(m))
            except Exception:
                pass
    return active


def get_upcoming_feed_machines(buffer_minutes=60) -> set:
    if not CRON_MODULE_AVAILABLE:
        return set()
    try:
        root = Path(r"D:\Taadaa\runtime\kibe\cron-state")
        source_file = Path(r"D:\Taadaa\runtime\kibe\cron-source\hermes_cron_source_config.json")
        if not root.exists() or not source_file.exists():
            return set()
        source = SourceConfig.from_json(source_file)
        now_dt = datetime.now().astimezone(parse_hcm_timestamp("2026-08-18T00:00:00+07:00").tzinfo)
        day_str = now_dt.strftime("%Y-%m-%d")
        active = load_active(StatePaths(root, root), day_str, source)
        busy_window_end = now_dt + timedelta(minutes=buffer_minutes)
        busy_machines = set()
        for entry in active.payload.get("entries", []):
            m = entry.get("machine")
            if m is None:
                continue
            s_start = parse_hcm_timestamp(entry["slot_time"])
            s_end = parse_hcm_timestamp(entry["slot_end"])
            if (s_start <= now_dt < s_end) or (now_dt <= s_start < busy_window_end):
                busy_machines.add(int(m))
        return busy_machines
    except Exception as e:
        log(f"Lỗi khi đọc manifest cron nuôi acc: {e}")
        return set()


def scan_candidates() -> list:
    if not CLEAN_XLSX.exists():
        log(f"Không tìm thấy file: {CLEAN_XLSX}")
        return []
    import openpyxl
    wb = openpyxl.load_workbook(CLEAN_XLSX, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))[1:]
    wb.close()

    today = date.today()
    candidates = []
    for r in rows:
        stt = r[0]
        email = str(r[1] or "").strip().lower()
        two_fa = r[3]
        created = r[6]
        if not email.endswith("@gmail.com"):
            continue
        if two_fa is not None and str(two_fa).strip() not in ("", "None", "null"):
            continue
        if not created or not stt:
            continue
        try:
            m = int(stt)
            if isinstance(created, datetime):
                dt = created.date()
            elif isinstance(created, date):
                dt = created
            else:
                dt = datetime.strptime(str(created)[:10], "%Y-%m-%d").date()
            days_ago = (today - dt).days
            if days_ago >= 1:
                candidates.append({
                    "machine": m,
                    "email": email,
                    "days_ago": days_ago,
                    "created": str(dt)
                })
        except Exception:
            pass
    return candidates


def main():
    parser = argparse.ArgumentParser(description="Watchdog bật 2FA Gmail sau Ca 1.")
    parser.add_argument("--dry-run", action="store_true", help="Chạy giả lập, không tác động thiết bị")
    parser.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra giờ và trạng thái feed/lock")
    args = parser.parse_args()

    # 1. Kiểm tra idempotency
    if not args.force and is_already_run_today():
        return 0

    # 2. Kiểm tra khung giờ (08:30 - 11:30)
    if not args.force and not is_within_time_window((8, 30), (11, 30)):
        return 0

    # 3. Kiểm tra ca 1 hoàn thành
    if not args.force and not is_feed_ca1_finished():
        return 0

    # 4. Kiểm tra Idle
    if not args.force:
        if is_feed_runner_active():
            return 0

    candidates = scan_candidates()
    if not candidates:
        return 0

    online = get_online_devices()
    active_locks = get_active_locks()
    busy_feed = get_upcoming_feed_machines(buffer_minutes=60)

    import openpyxl
    if not PROXY_XLSX.exists():
        log(f"Không tìm thấy file: {PROXY_XLSX}")
        return 0

    wb_proxy = openpyxl.load_workbook(PROXY_XLSX, read_only=True)
    ws_proxy = wb_proxy.active
    serials = {}
    for r in list(ws_proxy.iter_rows(values_only=True))[1:]:
        if r[0] and r[1]:
            try:
                serials[int(r[0])] = str(r[1]).strip()
            except Exception:
                pass
    wb_proxy.close()

    eligible = []
    for c in candidates:
        m = c["machine"]
        s = serials.get(m)
        if not s or s not in online:
            continue
        if not args.force:
            if m in active_locks:
                continue
            if m in busy_feed:
                continue
        eligible.append((m, s, c["email"]))

    if not eligible:
        return 0

    start_time = datetime.now()
    success_list = []
    fail_list = []

    for m, s, email in eligible:
        log(f"-> Bắt đầu bật 2FA Máy {m} ({s}): {email}")
        if args.dry_run:
            success_list.append(f"M{m} ({email})")
            continue

        if enable_2fa_device:
            try:
                res = enable_2fa_device(s, email)
                if isinstance(res, dict) and res.get("status") in ["SUCCESS", "OK"]:
                    success_list.append(f"M{m} ({email})")
                else:
                    fail_list.append(f"M{m} ({email})")
            except Exception as e:
                log(f"Lỗi khi chạy enable_2fa_device cho M{m}: {e}")
                fail_list.append(f"M{m} ({email})")
        else:
            cmd = [sys.executable, r"D:\Taadaa\tools\enable_gmail_2fa_device.py", s, email]
            try:
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if p.returncode == 0 and "SUCCESS" in p.stdout:
                    success_list.append(f"M{m} ({email})")
                else:
                    fail_list.append(f"M{m} ({email})")
            except Exception as e:
                log(f"Lỗi thực thi lệnh M{m}: {e}")
                fail_list.append(f"M{m} ({email})")

    end_time = datetime.now()
    duration_min = round((end_time - start_time).total_seconds() / 60, 1)

    if success_list or fail_list:
        report = f"""[BÁO CÁO 2FA GMAIL SAU CA SÁNG]
- Thời gian: {start_time.strftime('%H:%M')} -> {end_time.strftime('%H:%M')} ({duration_min} phút)
- Tổng máy xử lý: {len(eligible)}
- Success ({len(success_list)}): {success_list}
- Fail ({len(fail_list)}): {fail_list}"""
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

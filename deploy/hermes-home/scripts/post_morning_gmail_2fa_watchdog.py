#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
post_morning_gmail_2fa_watchdog.py
Watchdog cuốn chiếu: Bật 2FA Google Authenticator cho các Profile GPM sau Ca 1 nuôi feed.
Khung giờ: 08:30 - 11:30 (HCM).
Silent Watchdog: Tuyệt đối không in ra stdout nếu không có kết quả hành động.
"""

import os
import sys
import re
import json
import time
import sqlite3
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
STATE_DIR = Path("D:/Taadaa/runtime/kibe/cron-state")
STATE_FILE = STATE_DIR / "post_morning_gmail_2fa_state.json"
FEED_REPORTED_FILE = STATE_DIR / "feed_session_reported.json"
GPM_DB_PATH = Path(r"C:\Users\Kibe\AppData\Local\Programs\GPMLogin\profile\profile_data.db")
MASTER_EXCEL = Path(r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx")
CLEAN_V2_EXCEL = Path(r"D:\OneDrive\TaadaaData\kibe\gmail_clean_v2.xlsx")

# Add GPM auto script to path for setup_authenticator_for_profile
GPM_SCRIPTS_DIR = Path(r"D:\Taadaa\GPM auto\scripts")
if str(GPM_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(GPM_SCRIPTS_DIR))

try:
    from run_add_2fa_remaining import setup_authenticator_for_profile
except ImportError:
    setup_authenticator_for_profile = None


def log(msg: str):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sys.stderr.write(f"[{now_str}] {msg}\n")


def is_within_time_window(start_hm=(8, 30), end_hm=(11, 30)) -> bool:
    now = datetime.now()
    cur_hm = (now.hour, now.minute)
    return start_hm <= cur_hm <= end_hm


def is_feed_ca1_finished() -> bool:
    if not FEED_REPORTED_FILE.exists():
        return False
    try:
        with open(FEED_REPORTED_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        today = datetime.now().strftime("%Y-%m-%d")
        keys = [f"{today}_ca1_phien2", f"{today}_ca1", f"{today}_ca1_phien3"]
        if isinstance(data, dict):
            reported = set(data.get("reported_sessions", []))
            return any(k in reported for k in keys) or any(k in data and data[k] for k in keys)
        elif isinstance(data, list):
            return any(isinstance(item, str) and any(k in item for k in keys) for item in data)
        return False
    except Exception as e:
        log(f"Lỗi kiểm tra feed session reported: {e}")
        return False


def get_gpm_candidates(limit: int = 5) -> list:
    """Lấy danh sách profile GPM cần bật 2FA (có email @gmail.com, có password, chưa có 2FA)."""
    if not GPM_DB_PATH.exists() or not MASTER_EXCEL.exists():
        return []

    import openpyxl

    master_pwd = {}
    master_2fa = {}
    try:
        wb_m = openpyxl.load_workbook(MASTER_EXCEL, read_only=True, data_only=True)
        if "Master_All" in wb_m.sheetnames:
            ws = wb_m["Master_All"]
            for r in list(ws.iter_rows(values_only=True))[1:]:
                em = str(r[1] or "").strip().lower()
                if em:
                    master_pwd[em] = str(r[2] or "").strip()
                    if len(r) > 4 and r[4]:
                        master_2fa[em] = str(r[4] or "").strip()
        wb_m.close()
    except Exception as e:
        log(f"Lỗi đọc MASTER_EXCEL: {e}")

    clean_pwd = {}
    clean_2fa = {}
    if CLEAN_V2_EXCEL.exists():
        try:
            wb_c = openpyxl.load_workbook(CLEAN_V2_EXCEL, read_only=True, data_only=True)
            ws_c = wb_c.active
            for r in list(ws_c.iter_rows(values_only=True))[1:]:
                em = str(r[1] or "").strip().lower()
                if em:
                    clean_pwd[em] = str(r[2] or "").strip()
                    if len(r) > 3 and r[3]:
                        clean_2fa[em] = str(r[3] or "").strip()
            wb_c.close()
        except Exception as e:
            log(f"Lỗi đọc CLEAN_V2_EXCEL: {e}")

    candidates = []
    try:
        conn = sqlite3.connect(GPM_DB_PATH)
        c = conn.cursor()
        c.execute("SELECT Id, Name, ProfilePath, GroupId FROM Profiles ORDER BY Id ASC")
        rows = c.fetchall()
        conn.close()

        for pid, name, ppath, gid in rows:
            if not name or name.startswith("AMZ_") or "deleted" in name.lower():
                continue
            em_match = re.search(r"([a-zA-Z0-9_.+-]+@gmail\.com)", name, re.IGNORECASE)
            if not em_match:
                continue
            email = em_match.group(1).lower()

            sec = master_2fa.get(email) or clean_2fa.get(email) or ""
            if sec and sec not in ("", "None", "null"):
                continue

            pwd = master_pwd.get(email) or clean_pwd.get(email) or ""
            if not pwd:
                continue

            m_match = re.match(r"^(\d+)", name) or re.search(r"M(\d+)", name, re.IGNORECASE)
            machine_num = int(m_match.group(1)) if m_match else 0

            candidates.append({
                "id": pid,
                "name": name,
                "email": email,
                "machine": machine_num,
                "pwd": pwd,
                "2fa_secret": "",
                "group_id": gid
            })
            if len(candidates) >= limit:
                break
    except Exception as e:
        log(f"Lỗi truy vấn GPM database: {e}")

    return candidates


def save_state_results(success_list: list, fail_list: list):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        data = {
            "last_run_date": today,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": success_list,
            "failed": fail_list
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"Lỗi ghi state: {e}")


def main():
    parser = argparse.ArgumentParser(description="Watchdog bật 2FA cho profile GPM sau Ca 1.")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ quét candidates, không thực thi")
    parser.add_argument("--force", action="store_true", help="Bỏ qua kiểm tra giờ và feed session")
    parser.add_argument("--batch-size", type=int, default=5, help="Số profile xử lý tối đa mỗi tick")
    args = parser.parse_args()

    if not args.force and not is_within_time_window((8, 30), (11, 30)):
        return 0

    if not args.force and not is_feed_ca1_finished():
        return 0

    candidates = get_gpm_candidates(limit=args.batch_size)
    if not candidates:
        return 0

    if args.dry_run:
        log(f"[DRY-RUN] Tìm thấy {len(candidates)} profile GPM cần bật 2FA:")
        for c in candidates:
            log(f"  - Máy {c['machine']:02d} | {c['name']} ({c['email']})")
        return 0

    if not setup_authenticator_for_profile:
        log("Lỗi: Không thể import setup_authenticator_for_profile từ GPM auto")
        return 1

    success_list = []
    fail_list = []

    for c in candidates:
        try:
            log(f"Bắt đầu xử lý 2FA GPM: {c['name']} ({c['email']})...")
            res = setup_authenticator_for_profile(c)
            if res.get("status") == "SUCCESS" and res.get("secret_key"):
                success_list.append(f"{c['email']} ({res['secret_key']})")
            elif res.get("status") == "ALREADY_ACTIVE":
                success_list.append(f"{c['email']} (ALREADY_ACTIVE)")
            else:
                fail_list.append(f"{c['email']}: {res.get('status')} - {res.get('details')}")
        except Exception as e:
            log(f"Exception khi xử lý {c['email']}: {e}")
            fail_list.append(f"{c['email']}: {str(e)}")

    if success_list:
        save_state_results(success_list, fail_list)
        report = [
            "### [BÁO CÁO 2FA GMAIL QUA GPM PROFILE]",
            f"- Đã xử lý: {len(candidates)} profile",
            f"- Thành công ({len(success_list)}):",
        ]
        for s in success_list:
            report.append(f"  + {s}")
        if fail_list:
            report.append(f"- Cần lưu ý ({len(fail_list)}):")
            for f_item in fail_list:
                report.append(f"  + {f_item}")
        print("\n".join(report))

    return 0


if __name__ == "__main__":
    sys.exit(main())

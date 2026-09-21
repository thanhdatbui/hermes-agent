#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_gpm_lifecycle.py
Quản lý vòng đời Profile GPM & S7 tự động:
1. DỌN DẸP GPM: Xóa bỏ các profile GPM gắn với Gmail đã bị DIE / BAN / SUSPENDED.
2. TẠO MỚI GPM: Tự động tạo profile GPM chuẩn cho các Gmail LIVE mới (kèm proxy 4G tương ứng trên S7).
3. DỌN DẸP S7 CUỐN CHIẾU: Chỉ chạy buổi sáng (07:15 - 08:45), kẹp non-blocking device lock & manifest check.
"""

from __future__ import annotations

import os
import sys
import re
import json
import glob
import sqlite3
import logging
import argparse
import requests
import openpyxl
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HCMC = ZoneInfo("Asia/Ho_Chi_Minh")

# Thêm đường dẫn src để import GPMClient
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

GPM_AUTO_SRC = Path(r"D:\Taadaa\GPM auto\src")
if GPM_AUTO_SRC.exists() and str(GPM_AUTO_SRC) not in sys.path:
    sys.path.insert(0, str(GPM_AUTO_SRC))

# Thêm đường dẫn automation-core để lấy acquire_device_lock
CORE_DIR = Path(r"D:\Taadaa\automation-core\src")
if CORE_DIR.exists() and str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

try:
    from gpm_client import GPMClient
except ImportError:
    GPMClient = None

try:
    from automation_core.device_lock import acquire_device_lock, DeviceLockUnavailable
except Exception:
    acquire_device_lock = None
    DeviceLockUnavailable = Exception

GPM_API_BASE = "http://127.0.0.1:19995/api/v3"
PROXY_FILE   = r"D:\OneDrive\TaadaaData\kibe\PROXYgandienthoai.xlsx"
MASTER_FILE  = r"D:\OneDrive\TaadaaData\kibe\master_gmail_manager.xlsx"
STATUS_FILE  = r"D:\Taadaa\GPM auto\config\oauth_pipeline_status.json"
GPM_DB       = Path.home() / "AppData" / "Local" / "Programs" / "GPMLogin" / "profile" / "profile_data.db"
ADB_PATH     = r"C:\Program Files (x86)\xiaowei\tools\adb.exe"
MANIFEST_DIR = Path(r"D:\Taadaa\runtime\kibe\cron-state\manifests")
LOG_DIR      = Path(r"D:\Taadaa\GPM auto\logs")
LOG_FILE     = LOG_DIR / "sync_gpm_lifecycle.log"

# Logging setup
LOG_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger("sync_gpm_lifecycle")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(str(LOG_FILE), encoding="utf-8")
    fh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(fh)


def log_telemetry_metric(event_type: str, data: dict):
    """Ghi nhận telemetry metric có cấu trúc JSON để phục vụ quan sát hệ thống & watchdog."""
    metric = {
        "timestamp": datetime.now(HCMC).isoformat(),
        "event": event_type,
        "pid": os.getpid(),
        "data": data
    }
    logger.info(f"[TELEMETRY_METRIC] {json.dumps(metric, ensure_ascii=False)}")
    return metric


def get_online_adb_devices() -> set[str]:
    """Lấy danh sách các serial thiết bị ADB đang ở trạng thái online / device."""
    online_devs = set()
    try:
        res = subprocess.run([ADB_PATH, "devices"], capture_output=True, text=True, timeout=5)
        for l in res.stdout.splitlines():
            if "\tdevice" in l:
                online_devs.add(l.split()[0].strip())
    except Exception as e:
        logger.warning(f"Lỗi khi kiểm tra adb devices: {e}")
    return online_devs


def is_gpm_api_live() -> bool:
    try:
        r = requests.get(f"{GPM_API_BASE}/profiles?limit=1", timeout=3)
        return r.status_code == 200 and r.json().get("success") is True
    except Exception:
        return False


def is_morning_cleanup_window() -> bool:
    """Chỉ kích hoạt dọn thiết bị S7 buổi sáng (07:15 - 08:45 HCM)."""
    now = datetime.now(HCMC)
    current_min = now.hour * 60 + now.minute
    return 7 * 60 + 15 <= current_min <= 8 * 60 + 45


def is_machine_in_feed_slot(mid: int) -> bool:
    """Kiểm tra máy có đang trong slot nuôi hoặc sắp nuôi trong 30 phút tới không."""
    now_dt = datetime.now()
    dirs = glob.glob(str(MANIFEST_DIR / "*"))
    if not dirs:
        return False
    latest_dir = max(dirs, key=os.path.getmtime)
    files = glob.glob(os.path.join(latest_dir, "assignment-v1-*.json"))
    if not files:
        return False
    try:
        mdata = json.loads(Path(max(files, key=os.path.getmtime)).read_text(encoding="utf-8"))
        for e in mdata.get("entries", []):
            if e.get("machine") == mid:
                st = datetime.fromisoformat(e["slot_time"]).replace(tzinfo=None)
                et = datetime.fromisoformat(e["slot_end"]).replace(tzinfo=None)
                if (st <= now_dt < et) or (now_dt <= st < now_dt + timedelta(minutes=30)):
                    return True
    except Exception:
        pass
    return False


def sync_lifecycle_gpm():
    logger.info("Bắt đầu đồng bộ lifecycle GPM...")
    if GPMClient is None:
        logger.error("GPMClient is None, cannot proceed")
        return

    if not is_gpm_api_live():
        logger.warning("GPM API không hoạt động, bỏ qua sync_lifecycle_gpm.")
        return

    client = GPMClient(base_url=GPM_API_BASE)

    # 1. Đọc Master Excel
    if not os.path.exists(MASTER_FILE):
        logger.warning(f"Không tìm thấy Master Excel: {MASTER_FILE}")
        return

    wb = openpyxl.load_workbook(MASTER_FILE, data_only=True, read_only=True)
    ws = wb["Kibe_Farm_S7"]
    die_emails = set()
    live_candidates = {}

    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not (r and r[1] and "@" in str(r[1])):
            continue
        email = str(r[1]).strip().lower()
        status = str(r[6] or "").strip().upper()
        recovery = str(r[3] or "").strip().lower()
        mid_str = str(r[7] or "")
        m_mid = re.search(r"(\d+)", mid_str)
        mid = int(m_mid.group(1)) if m_mid else None

        if status in ("DIE", "BAN", "SUSPENDED"):
            die_emails.add(email)
        elif status == "LIVE":
            if "khoale" in email or "khoale" in recovery:
                continue
            if mid:
                live_candidates[email] = mid
    wb.close()

    # 2. Đọc GPM SQLite DB
    if not GPM_DB.exists():
        logger.warning(f"Không tìm thấy GPM DB: {GPM_DB}")
        return

    conn = sqlite3.connect(str(GPM_DB))
    cur = conn.cursor()
    cur.execute("SELECT Id, Name FROM profiles;")
    gpm_profiles = cur.fetchall()
    conn.close()

    existing_gpm_emails = set()
    for pid, name in gpm_profiles:
        if not name:
            continue
        for em in re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", name.lower()):
            existing_gpm_emails.add(em)

    # --- BỎ QUA XÓA PROFILE GPM DIE ĐỂ BẢO TOÀN SESSION / VER SỐ (TÀI SẢN FARM) ---
    logger.info("Chính sách an toàn: Bỏ qua xóa profile GPM DIE (bảo toàn tài khoản/session OpenAI/Codex đã ver số).")
    log_telemetry_metric("gpm_lifecycle_sync_die_skipped", {
        "die_emails_in_master": len(die_emails),
        "reason": "preserve_openai_codex_sessions"
    })

    # --- TIẾN HÀNH TẠO PROFILE CHO GMAIL LIVE MỚI ---
    status_exclusions = set()
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                sdata = json.load(f)
            for k in ["omniroute_success", "excluded_khoalee", "wrong_password_or_checkpoint"]:
                val = sdata.get(k, {})
                if isinstance(val, dict):
                    status_exclusions.update(x.lower() for x in val.keys())
                elif isinstance(val, list):
                    status_exclusions.update(x.lower() for x in val)
        except Exception:
            pass

    proxy_map = {}
    serials = {}
    if os.path.exists(PROXY_FILE):
        wb_p = openpyxl.load_workbook(PROXY_FILE, data_only=True, read_only=True)
        ws_p = wb_p["Proxy"]
        for r in list(ws_p.iter_rows(values_only=True))[1:]:
            if r and r[0] is not None:
                try:
                    m_idx = int(r[0])
                    if r[1]:
                        serials[m_idx] = str(r[1]).strip()
                    if r[2]:
                        proxy_map[m_idx] = str(r[2]).strip()
                except Exception:
                    pass
        wb_p.close()

    # Kiểm tra thiết bị ADB online trước khi tạo profile LIVE
    online_devs = get_online_adb_devices()

    created_count = 0
    for email, mid in live_candidates.items():
        if email in existing_gpm_emails or email in status_exclusions:
            continue
        if mid not in proxy_map:
            continue

        # Kiểm tra máy mid có serial và serial phải online ADB
        serial = serials.get(mid)
        if not serial or serial not in online_devs:
            logger.info(f"Bỏ qua tạo profile cho {email} vì máy M{mid:02d} (serial={serial}) không online ADB.")
            continue

        raw_proxy = proxy_map[mid]
        m_port = re.search(r":(\d{4,5}):", raw_proxy)
        port = m_port.group(1) if m_port else ""
        prof_name = f"{mid:02d} - {email} - {port}"

        try:
            res = client.create_profile(
                name=prof_name,
                raw_proxy=raw_proxy,
                group_id=1
            )
            if res.get("success"):
                created_count += 1
                existing_gpm_emails.add(email)
                logger.info(f"Đã tạo profile GPM: {prof_name}")
        except Exception as e:
            logger.error(f"Lỗi khi tạo profile {prof_name}: {e}")

    if created_count > 0:
        logger.info(f"[GPM LIFECYCLE] Tạo mới {created_count} profile LIVE")
    log_telemetry_metric("gpm_lifecycle_sync_completed", {
        "created_count": created_count,
        "live_candidates_total": len(live_candidates),
        "existing_gpm_profiles": len(gpm_profiles)
    })
    return created_count


def cleanup_s7_die_accounts(dry_run: bool = False, force: bool = False):
    """Dọn dẹp tài khoản Gmail DIE trên thiết bị S7 qua cơ chế cuốn chiếu an toàn."""
    if not force and not is_morning_cleanup_window():
        return

    logger.info("Bắt đầu dọn dẹp tài khoản Gmail DIE trên thiết bị S7...")

    # 1. Đọc mapping DIE từ Master Excel
    if not os.path.exists(MASTER_FILE):
        logger.warning(f"Không tìm thấy Master Excel: {MASTER_FILE}")
        return

    wb = openpyxl.load_workbook(MASTER_FILE, data_only=True, read_only=True)
    ws = wb["Kibe_Farm_S7"]
    die_by_mid = {}
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if not (r and r[1]):
            continue
        st = str(r[6] or "").strip().upper()
        if st in ("DIE", "BAN", "SUSPENDED"):
            mid_str = str(r[7] or "")
            m_mid = re.search(r"(\d+)", mid_str)
            if m_mid:
                mid = int(m_mid.group(1))
                die_by_mid.setdefault(mid, []).append(str(r[1]).strip().lower())
    wb.close()

    if not die_by_mid:
        logger.info("Không có tài khoản DIE cần gỡ trên S7.")
        return

    # 2. Đọc serial mapping
    serials = {}
    if os.path.exists(PROXY_FILE):
        wb_p = openpyxl.load_workbook(PROXY_FILE, data_only=True, read_only=True)
        ws_p = wb_p["Proxy"]
        for r in list(ws_p.iter_rows(values_only=True))[1:]:
            if r and r[0] is not None and r[1]:
                try:
                    serials[int(r[0])] = str(r[1]).strip()
                except Exception:
                    pass
        wb_p.close()

    # 3. Lấy devices ADB online
    online_devs = get_online_adb_devices()
    if not online_devs:
        logger.warning("Không có thiết bị ADB nào online.")
        return

    # 4. Quét từng máy có DIE
    cleaned_count = 0
    for mid, dies in sorted(die_by_mid.items()):
        serial = serials.get(mid)
        if not serial or serial not in online_devs:
            continue

        # Tránh ca nuôi TikTok
        if is_machine_in_feed_slot(mid):
            logger.info(f"Máy M{mid:02d} đang trong slot feed, bỏ qua.")
            continue

        if not acquire_device_lock:
            continue

        # Thử lấy lock (non-blocking: nếu đang bận nuôi thì bỏ qua máy này để sang máy khác)
        try:
            with acquire_device_lock(machine=str(mid), serial=serial, project="gpm-cleanup", bypass_proxy_readiness=True):
                # Kiểm tra dumpsys account xem email DIE có thực sự còn trên máy không
                try:
                    chk = subprocess.run([ADB_PATH, "-s", serial, "shell", "dumpsys", "account"], capture_output=True, text=True, timeout=5)
                    dev_accs = [a.lower() for a in re.findall(r"Account \{name=([^,]+), type=com\.google\}", chk.stdout)]
                except Exception:
                    dev_accs = []

                hit_emails = [em for em in dies if em in dev_accs]
                if not hit_emails:
                    continue

                for target_email in hit_emails:
                    if dry_run:
                        logger.info(f"[DRY-RUN] [M{mid:02d}] Sẽ gỡ {target_email} khỏi S7 ({serial})")
                        cleaned_count += 1
                        continue

                    # Gọi script gỡ chuẩn farm
                    sys.path.insert(0, r"D:\Taadaa\GPM auto\scripts")
                    try:
                        from preflight_s7_rolling_cleanup import remove_account_adb
                        ok = remove_account_adb(serial, mid, target_email, dry_run=False, skip_lock=True)
                        if ok:
                            cleaned_count += 1
                            logger.info(f"[S7 CLEANUP] [M{mid:02d}] Đã gỡ thành công {target_email}")
                    except Exception as ex_del:
                        logger.error(f"Lỗi khi gỡ account {target_email}: {ex_del}")
                
                # Đưa về HOME an toàn
                subprocess.run([ADB_PATH, "-s", serial, "shell", "input", "keyevent", "3"], capture_output=True, timeout=5)
        except DeviceLockUnavailable:
            # Máy đang bận, bỏ qua sang máy khác
            continue
        except Exception as e:
            logger.warning(f"Lỗi xử lý máy M{mid:02d}: {e}")
            continue

    if cleaned_count > 0:
        logger.info(f"[S7 LIFECYCLE] Hoàn tất dọn dẹp {cleaned_count} tài khoản DIE trên thiết bị S7.")
    log_telemetry_metric("s7_cleanup_completed", {
        "cleaned_count": cleaned_count,
        "die_machines_count": len(die_by_mid)
    })
    return cleaned_count


def main():
    parser = argparse.ArgumentParser(description="GPM & S7 Lifecycle Sync Watchdog")
    parser.add_argument("--dry-run", action="store_true", help="Chạy thử nghiệm không xóa thật")
    parser.add_argument("--force-s7", action="store_true", help="Bỏ qua kiểm tra khung giờ sáng để test dọn S7")
    parser.add_argument("-v", "--verbose", action="store_true", help="In chi tiết log ra console / stdout")
    args = parser.parse_args()

    if args.verbose:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
        logger.addHandler(sh)

    created_cnt = sync_lifecycle_gpm() or 0
    cleaned_cnt = cleanup_s7_die_accounts(dry_run=args.dry_run, force=args.force_s7) or 0

    if created_cnt > 0 or cleaned_cnt > 0:
        parts = []
        if created_cnt > 0:
            parts.append(f"Tạo mới {created_cnt} profile LIVE")
        if cleaned_cnt > 0:
            parts.append(f"Đã dọn {cleaned_cnt} tài khoản DIE trên S7")
        print(f"[GPM & S7 LIFECYCLE] {' | '.join(parts)}")


if __name__ == "__main__":
    main()
